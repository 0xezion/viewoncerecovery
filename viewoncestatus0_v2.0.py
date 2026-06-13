# -*- coding: utf-8 -*-
#!/usr/bin/env python3

import sqlite3
import os
import platform
import hashlib
import hmac
import threading
import queue
import subprocess
import webbrowser
from Crypto.Cipher import AES
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ===================== CRYPTO CORE & INFORMATION =====================

appInfo = {
    "audio":    b"WhatsApp Audio Keys",
    "video":    b"WhatsApp Video Keys",
    "image":    b"WhatsApp Image Keys",
    "document": b"WhatsApp Document Keys"
}

def validar_e_detectar_integridade(file_path):
    """
    Realiza a validação estrutural do container decifrado para evitar falsos positivos.
    """
    if not os.path.exists(file_path):
        return None
    
    tamanho = os.path.getsize(file_path)
    if tamanho < 16:
        return None

    with open(file_path, "rb") as f:
        header = f.read(64)

    # Imagens
    if header.startswith(b"\xff\xd8\xff"):
        if tamanho > 100: 
            return "jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return "gif"
        
    # Áudio
    if header.startswith(b"OggS"): 
        return "opus"
    if header.startswith(b"#!AMR"): 
        return "amr"
    if header.startswith(b"RIFF") and header[8:12] == b"WAVE": 
        return "wav"
    if header.startswith(b"ID3") or header.startswith(b"\xff\xfb"): 
        return "mp3"
        
    # Container MP4 estrutural
    if b"ftyp" in header:
        if tamanho > 1024:
            return "mp4"
            
    return None

def unpad_pkcs7(data):
    if len(data) == 0:
        raise ValueError("Payload decifrado está vazio.")
    pad_len = data[-1]
    if pad_len < 1 or pad_len > 16:
        raise ValueError(f"Tamanho de padding PKCS#7 inválido ({pad_len}).")
    for i in range(len(data) - pad_len, len(data)):
        if data[i] != pad_len:
            raise ValueError("Bytes de preenchimento PKCS#7 inconsistentes.")
    return data[:-pad_len]

def force_decrypt_media(enc_path, media_key_bytes, media_type):
    if not media_key_bytes or not isinstance(media_key_bytes, bytes):
        raise ValueError("Material de chave criptográfica inválido ou ausente.")

    with open(enc_path, "rb") as f:
        enc_data = f.read()

    info_str = appInfo.get(media_type, b"WhatsApp Image Keys")
    salt = b"\x00" * 32
    
    prk = hmac.new(salt, media_key_bytes, hashlib.sha256).digest()
    derivative = b""
    prev = b""
    for i in range(1, 4):
        prev = hmac.new(prk, prev + info_str + bytes([i]), hashlib.sha256).digest()
        derivative += prev

    iv = derivative[:16]
    cipher_key = derivative[16:48]

    if len(enc_data) <= 26:
        raise ValueError("Tamanho de payload .enc insuficiente.")

    cipher_data = enc_data[:-10]
    if len(cipher_data) % 16 != 0:
        raise ValueError(f"Erro de alinhamento de bloco AES-CBC ({len(cipher_data)} bytes).")

    cipher = AES.new(cipher_key, AES.MODE_CBC, iv)
    decrypted_raw = cipher.decrypt(cipher_data)
    return unpad_pkcs7(decrypted_raw)

def convert_android_date(ts):
    try:
        return datetime.fromtimestamp(int(ts)/1000).strftime("%d/%m/%Y %H:%M:%S")
    except:
        return "Data Inválida"

# ===================== ENGINE DE REDE (SUPER-VERBOSE MODE - cURL) =====================

def executar_curl_download_verbose(url, enc_path, id_row, local_logs):
    """
    Executa o cURL e captura os metadados. Para uso em threads, preenche logs numa lista local 
    em vez de jogar direto na UI para evitar colisão de textos.
    """
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    cmd = [
        "curl", "-L", "-v", 
        "--max-time", "25", 
        "--connect-timeout", "8",
        "-H", "User-Agent: WhatsApp/2.24.4.78 Android/13 (Linux; U; Android 13; pt_BR; SM-G998B Build/TP1A.220624.014)",
        "-H", "Accept-Encoding: gzip, deflate",
        "-H", "Accept: */*",
        "-o", enc_path, url
    ]

    local_logs.append((f"[DEBUG-REDE] Comando Executado: {' '.join(cmd)}", "yellow"))
    
    try:
        proc = subprocess.Popen(cmd, startupinfo=startupinfo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="ignore")
        _, stderr = proc.communicate()
        
        if stderr:
            local_logs.append((f"--- INÍCIO DOS METADADOS DE COMUNICAÇÃO (ID {id_row}) ---", "cyan"))
            for line in stderr.splitlines():
                if line.strip():
                    local_logs.append((f" [cURL LOG] {line}", "gray"))
            local_logs.append(("--- FIM DOS METADADOS DE COMUNICAÇÃO ---", "cyan"))
            
        return os.path.exists(enc_path) and os.path.getsize(enc_path) > 0
    except Exception as e:
        local_logs.append((f"[-] Erro crítico de execução do subprocesso de rede: {str(e)}", "red"))
        return False

# ===================== TASK PARALELA INDIVIDUAL =====================

def processar_registro_individual(row, output_dir, enc_folder, ui_queue):
    id_row          = int(row[0])
    raw_url         = row[1]
    media_key       = row[2]
    e2ee_media_key  = row[3]
    mime_type       = row[5]
    timestamp       = int(row[6]) if row[6] else 0
    origin          = int(row[7]) if row[7] else 0
    phone           = row[8].decode('utf-8', errors='ignore') if row[8] else "Desconhecido"
    view_once_state = int(row[9]) if row[9] else 0
    media_name      = row[10]
    raw_text_data   = row[13]

    legenda_texto = "N/A (Sem legenda atrelada)"
    if raw_text_data:
        legenda_texto = raw_text_data.decode('utf-8', errors='ignore').strip()

    local_logs = []
    local_logs.append(("==================================================", "white"))
    local_logs.append((f"[AUDITORIA LOG] VERIFICANDO ID: {id_row} | Estado Vinculado: {view_once_state}", "white"))
    
    chosen_key_material = None
    key_status_str = "AUSENTE"
    key_hex_log = "N/A"

    if media_key and len(media_key) > 0:
        chosen_key_material = media_key
        key_status_str = "DISPONÍVEL (media_key)"
        key_hex_log = media_key.hex()
        local_logs.append((f" -> media_key: DISPONÍVEL ({len(media_key)} bytes)", "green"))
    elif e2ee_media_key and len(e2ee_media_key) > 0:
        chosen_key_material = e2ee_media_key
        key_status_str = "DISPONÍVEL (e2ee_media_key)"
        key_hex_log = e2ee_media_key.hex()
        local_logs.append((f" -> e2ee_media_key: DISPONÍVEL ({len(e2ee_media_key)} bytes)", "green"))
    else:
        local_logs.append((" -> Chaves Criptográficas: AUSENTES (Registro impossibilitado de decifração)", "red"))

    def build_result(status_crypto, path="N/A", size=0, url_str="N/A"):
        return {
            "id": id_row, "phone": phone, "view_once_state": view_once_state,
            "path": path, "media_name": m_name if "m_name" in dir() else "Desconhecido", 
            "status_crypto": status_crypto,
            "date_human": convert_android_date(timestamp), "unix_timestamp": timestamp, "size": size,
            "origin": "Enviada" if origin == 1 else "Recebida",
            "key_material": key_hex_log, "key_status": key_status_str, "url_bruta": url_str,
            "legenda": legenda_texto
        }

    if not raw_url:
        local_logs.append((f"[-] Registro {id_row} ignorado: Metadado de URL nulo.", "red"))
        ui_queue.put({"action": "log_block", "data": {"logs": local_logs}})
        return build_result("Metadado de URL nulo no banco de dados.")

    url = raw_url.decode('utf-8', errors='ignore').strip().replace('\n', '').replace('\r', '')
    mime_str = mime_type.decode('utf-8', errors='ignore').lower() if mime_type else ""
    m_name = media_name.decode('utf-8', errors='ignore') if media_name else "Desconhecido"
    media_name_str = m_name.lower()
    
    if "audio" in mime_str or "voice" in mime_str or media_name_str.endswith(".opus"):
        ext, media_type, subpasta = "opus", "audio", "WhatsApp Voice Notes"
    elif "video" in mime_str or media_name_str.endswith(".mp4"):
        ext, media_type, subpasta = "mp4", "video", "WhatsApp Video"
    elif "image" in mime_str or media_name_str.endswith((".jpg", ".jpeg")):
        ext, media_type, subpasta = "jpg", "image", "WhatsApp Images"
    else:
        ext, media_type, subpasta = "bin", "document", "WhatsApp Documents"

    nome_arquivo_recuperado = f"view_once_status{view_once_state}_{id_row}.{ext}"
    file_path = f"Media/{subpasta}/{nome_arquivo_recuperado}"
    output_file = os.path.join(output_dir, file_path)
    enc_path = os.path.join(enc_folder, f"{id_row}.enc")

    download_success = executar_curl_download_verbose(url, enc_path, id_row, local_logs)
    
    if not download_success:
        local_logs.append((f"[-] Falha na requisição de rede cURL para o ID {id_row}", "red"))
        ui_queue.put({"action": "log_block", "data": {"logs": local_logs}})
        return build_result("Falha na requisição de rede cURL.", enc_path, 0, url)

    tam_arquivo_enc = os.path.getsize(enc_path)
    local_logs.append((f" -> Bytes totais armazenados no payload local: {tam_arquivo_enc} bytes", "white"))
    
    if tam_arquivo_enc <= 65:
        with open(enc_path, "rb") as f_res:
            string_residual = f_res.read().decode('utf-8', errors='ignore').strip()
        
        if "Content not found" in string_residual:
            status_cdn = 'O servidor retornou a resposta literal "Content not found" para a URL armazenada.'
        elif "URL signature expired" in string_residual:
            status_cdn = 'O servidor retornou a resposta literal "URL signature expired" para a URL armazenada.'
        else:
            status_cdn = f"Rejeição da CDN com resposta literal: '{string_residual}'"
            
        local_logs.append((f" -> [ALERTA CDN] {status_cdn}", "red"))
        ui_queue.put({"action": "add_list", "data": {"text": f"[Indisponível na CDN] ID: {id_row}", "is_error": True}})
        ui_queue.put({"action": "log_block", "data": {"logs": local_logs}})
        return build_result(status_cdn, enc_path, tam_arquivo_enc, url)

    if not chosen_key_material:
        status_cdn = "Payload retido, porém o material criptográfico está ausente no banco local."
        local_logs.append(("[-] Objeto retido possui dados, mas a chave criptográfica é inexistente no banco.", "red"))
        ui_queue.put({"action": "add_list", "data": {"text": f"[Chave Ausente] ID: {id_row}", "is_error": True}})
        ui_queue.put({"action": "log_block", "data": {"logs": local_logs}})
        return build_result(status_cdn, enc_path, tam_arquivo_enc, url)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    status_report = "Erro Desconhecido"
    try:
        decrypted_bytes = force_decrypt_media(enc_path, chosen_key_material, media_type)
        with open(output_file, 'wb') as lf:
            lf.write(decrypted_bytes)
            
        ext_real = validar_e_detectar_integridade(output_file)
        if ext_real:
            if ext_real != ext:
                novo_output_file = output_file.rsplit('.', 1)[0] + f".{ext_real}"
                if os.path.exists(novo_output_file): os.remove(novo_output_file)
                os.rename(output_file, novo_output_file)
                output_file = novo_output_file
            
            local_logs.append((f"[+] Sucesso: Registro {id_row} decifrado e validado estruturalmente.", "cyan"))
            ui_queue.put({"action": "add_list", "data": {"text": f"{os.path.basename(output_file)}", "is_error": False}})
            status_report = "INTEGRIDADE_VALIDADA_OK"
        else:
            os.remove(output_file)
            local_logs.append((f"[-] Falha Estrutural: Arquivo {id_row} corrompido pós-decifração.", "red"))
            status_report = "Decifrado com sucesso, porém falhou na validação de integridade estrutural do container."
            ui_queue.put({"action": "add_list", "data": {"text": f"[Falha Estrutural] ID: {id_row}", "is_error": True}})
            
    except Exception as crypto_err:
        local_logs.append((f"[-] Falha na decifração AES/Unpadding: {crypto_err}", "red"))
        status_report = f"Falha crítica de decifração/unpadding (Dados corrompidos ou chave incorreta): {str(crypto_err)}"
        ui_queue.put({"action": "add_list", "data": {"text": f"[Erro Cripto] ID: {id_row}", "is_error": True}})

    ui_queue.put({"action": "log_block", "data": {"logs": local_logs}})
    
    return build_result(
        status_report,
        output_file if status_report == "INTEGRIDADE_VALIDADA_OK" else enc_path,
        tam_arquivo_enc, url
    )

# ===================== WORKER ORQUESTRADOR =====================

def process_database_worker(db_path, output_dir, limit_val, ui_queue):
    def post_ui(action, **kwargs):
        ui_queue.put({"action": action, "data": kwargs})

    post_ui("log", msg=f"[*] Inicializando varredura de auditoria forense: {db_path}", color_mode="cyan")
    
    db_user_version = 0
    total_tables = 0
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        
        cursor_meta = conn.cursor()
        cursor_meta.execute("PRAGMA user_version;")
        db_user_version = cursor_meta.fetchone()[0]
        cursor_meta.execute("SELECT count(*) FROM sqlite_master WHERE type='table';")
        total_tables = cursor_meta.fetchone()[0]
        
        conn.text_factory = bytes
        cursor = conn.cursor()
    except Exception as e:
        post_ui("log", msg=f"[-] Erro ao acessar base de dados: {str(e)}", color_mode="red")
        post_ui("finish", report_dir=output_dir)
        return

    query = """
        SELECT
            m._id, mm.message_url, mm.media_key, mm.e2ee_media_key, m.key_id,
            mm.mime_type, m.timestamp, m.from_me,
            CASE WHEN jr.raw_string IS NOT NULL THEN jr.raw_string ELSE jl.raw_string END AS phone,
            COALESCE(vom.state, 0) AS view_once_state, mm.media_name, mm.file_hash, mm.enc_file_hash,
            m.text_data
        FROM message m
        LEFT JOIN message_media mm ON mm.message_row_id = m._id
        LEFT JOIN message_view_once_media vom ON vom.message_row_id = m._id
        LEFT JOIN chat c ON c._id = m.chat_row_id
        LEFT JOIN jid jl ON jl._id = c.jid_row_id
        LEFT JOIN jid_map jm ON jm.lid_row_id = jl._id
        LEFT JOIN jid jr ON jr._id = jm.jid_row_id
        WHERE m.message_type IN (42, 43, 82)
        ORDER BY m.timestamp DESC
        LIMIT ?
    """

    try:
        cursor.execute(query, (limit_val,))
        rows = cursor.fetchall()
        post_ui("log", msg=f"[+] Alvos identificados na fila SQL: {len(rows)} registros.\n", color_mode="green")
    except Exception as e:
        post_ui("log", msg=f"[-] Erro na execução da Query: {str(e)}", color_mode="red")
        conn.close()
        post_ui("finish", report_dir=output_dir)
        return

    post_ui("set_max_progress", max_val=len(rows))
    report_entries = []
    enc_folder = os.path.join(output_dir, "_enc")
    os.makedirs(enc_folder, exist_ok=True)

    # Extração Paralela Dinâmica
    max_workers = min(5, max(2, len(rows) // 10))
    contador = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(processar_registro_individual, row, output_dir, enc_folder, ui_queue): row
            for row in rows
        }
        for future in as_completed(futures):
            contador += 1
            post_ui("update_progress", value=contador)
            try:
                result = future.result()
                if result:
                    report_entries.append(result)
            except Exception as exc:
                post_ui("log", msg=f"[!] Falha crítica na Thread: {exc}", color_mode="red")

    conn.close()
    
    # Ordena pelo timestamp antes de gerar o HTML
    report_entries.sort(key=lambda x: x["unix_timestamp"], reverse=True)
    
    post_ui("log", msg=f"\n[*] Processamento concluído. Gerando e instanciando relatório de saída...", color_mode="cyan")
    
    if report_entries:
        try:
            generate_report(report_entries, output_dir, db_user_version, total_tables)
            post_ui("log", msg=f"[+] Relatório instanciado com sucesso.", color_mode="green")
        except Exception as rep_err:
            post_ui("log", msg=f"[-] Erro crítico na compilação do arquivo HTML: {str(rep_err)}", color_mode="red")
            
    post_ui("finish", report_dir=output_dir)

# ===================== GERADOR E INSTANCIADOR DE RELATÓRIO =====================

def generate_report(entries, output_dir, db_version, total_tables):
    report_path = os.path.join(output_dir, "report.html")
    
    ok_rec = [e for e in entries if e["status_crypto"] == "INTEGRIDADE_VALIDADA_OK"]
    fail_rec = [e for e in entries if e["status_crypto"] != "INTEGRIDADE_VALIDADA_OK"]

    py_ver = platform.python_version()
    os_info = f"{platform.system()}-{platform.release()}"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("<html><head><meta charset='utf-8'><style>")
        f.write("body{font-family:'Segoe UI',sans-serif;margin:30px;background-color:#f4f6f9;color:#333;}")
        
        f.write(".main-title{font-size:22px; font-weight:bold; color:#111; margin-bottom:5px;}")
        f.write(".subtitle-bar{font-size:13px; color:#555; margin-bottom:15px;}")
        f.write(".tech-header-table{width:100%; background:#0d1117; color:#c9d1d9; border-collapse:collapse; font-size:11px; margin-bottom:20px; border-radius:4px; overflow:hidden;}")
        f.write(".tech-header-table td{padding:8px 14px; text-align:center; border-right:1px solid #21262d;}")
        f.write(".tech-header-table td:last-child{border-right:none;}")
        f.write(".tech-header-table span.label{color:#8b949e; text-transform:uppercase; font-weight:600; margin-right:5px;}")
        f.write(".tech-header-table span.value{color:#58a6ff; font-weight:bold;}")
        
        f.write(".secao-titulo{background:#e0e1dd; padding:10px 15px; border-radius:4px; margin-top:25px; font-weight:bold; border-left:5px solid #1b263b; font-size:15px;}")
        f.write(".card-header-clean{font-size:14px; margin-bottom:8px; padding-bottom:5px; border-bottom:1px solid rgba(0,0,0,0.1);}")
        
        # Estilos específicos para sucesso (Verde)
        f.write(".card-success{background:#e8f5e9;padding:15px;margin:12px 0;border-radius:6px;border-left:5px solid #2e7d32;font-size:13px;line-height:1.6;box-shadow: 0 1px 3px rgba(0,0,0,0.05);}")
        f.write(".card-success .meta-table td{padding:6px 10px; border:1px solid #c8e6c9; word-break:break-all; background:#fff;}")
        f.write(".card-success .meta-table td.title{background:#f1f8e9; font-weight:bold; width:18%; color:#1b5e20;}")
        
        # Estilos específicos para erro (Vermelho)
        f.write(".card-expired{background:#ffebee;padding:15px;margin:12px 0;border-radius:6px;border-left:5px solid #c62828;font-size:13px;line-height:1.6;box-shadow: 0 1px 3px rgba(0,0,0,0.05);}")
        f.write(".card-expired .meta-table td{padding:6px 10px; border:1px solid #ffcdd2; word-break:break-all; background:#fff5f5; color:#7f0000;}")
        f.write(".card-expired .meta-table td.title{background:#ffebee; font-weight:bold; width:18%; color:#b71c1c;}")

        f.write(".meta-table{width:100%; margin-top:8px; border-collapse:collapse; font-size:12px;}")
        f.write(".highlight-text{background:#fff9db; padding:2px 5px; border-radius:3px; font-weight:600; color:#b07a00;}")
        f.write("</style><title>Laudo Técnico Forense - Recuperação Residual de Mídias</title></head><body>")
        
        f.write("<div class='main-title'>Laudo Técnico Forense - Recuperação Residual de Mídias</div>")
        f.write(f"<div class='subtitle-bar'><b>Geração do Artefato:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} UTC | <b>Amostras Avaliadas:</b> {len(entries)}</div>")
        
        f.write("<table class='tech-header-table'><tr>")
        f.write(f"<td><span class='label'>Python:</span><span class='value'>{py_ver}</span></td>")
        f.write(f"<td><span class='label'>S.O.:</span><span class='value'>{os_info}</span></td>")
        f.write("<td><span class='label'>Cripto Core:</span><span class='value'>PyCryptodome-AES</span></td>")
        f.write("<td><span class='label'>cURL Bin:</span><span class='value'>Subprocess Native</span></td>")
        f.write(f"<td><span class='label'>DB User Version:</span><span class='value'>{db_version}</span></td>")
        f.write(f"<td><span class='label'>Tabelas DB:</span><span class='value'>{total_tables}</span></td>")
        f.write("</tr></table>")
        
        f.write(f"<div class='secao-titulo'>🟢 MÍDIAS EM CONFORMIDADE INTEGRAL CRIPTOGRÁFICA ({len(ok_rec)})</div>")
        for e in ok_rec:
            try: html_path = os.path.relpath(e["path"], output_dir).replace("\\", "/")
            except: html_path = "#"
            
            f.write(f"<div class='card-success'>")
            f.write(f"<div class='card-header-clean'><b>ID Mensagem (RowID):</b> <span style='background:#2e7d32; color:white; padding:1px 5px; border-radius:3px;'>{e['id']}</span> | <b>Estado do Registro:</b> {e['view_once_state']} | <b>Link:</b> 🔍 <a href='{html_path}' target='_blank'><b>{html_path}</b></a></div>")
            f.write("<table class='meta-table'>")
            f.write(f"<tr><td class='title'>Texto da Legenda</td><td><span class='highlight-text'>{e['legenda']}</span></td></tr>")
            f.write(f"<tr><td class='title'>Contato (JID/Phone)</td><td>{e['phone']}</td></tr>")
            f.write(f"<tr><td class='title'>Nome Original</td><td>{e['media_name']}</td></tr>")
            f.write(f"<tr><td class='title'>Status Chave</td><td>{e['key_status']}</td></tr>")
            f.write(f"<tr><td class='title'>Data do Registro</td><td>{e['date_human']}</td></tr>")
            f.write(f"<tr><td class='title'>Fluxo</td><td>{e['origin']}</td></tr>")
            f.write(f"<tr><td class='title'>Chave Simétrica (Hex)</td><td><code>{e['key_material']}</code></td></tr>")
            f.write(f"<tr><td class='title'>URL Completa Origem</td><td><code>{e['url_bruta']}</code></td></tr>")
            f.write("</table></div>")

        # Texto alterado e classes de estilo atualizadas sendo aplicadas
        f.write(f"<div class='secao-titulo'>🔴 CONTEÚDO INDISPONÍVEL OU NÃO LOCALIZADO NO ENDPOINT ({len(fail_rec)})</div>")
        for e in fail_rec:
            f.write(f"<div class='card-expired'>")
            f.write(f"<div class='card-header-clean'><b>ID Mensagem (RowID):</b> <span style='background:#c62828; color:white; padding:1px 5px; border-radius:3px;'>{e['id']}</span> | <b>Estado do Registro:</b> {e['view_once_state']}</div>")
            f.write("<table class='meta-table'>")
            f.write(f"<tr><td class='title'>Diagnóstico Forense</td><td><b>{e['status_crypto']}</b></td></tr>")
            f.write(f"<tr><td class='title'>Texto da Legenda</td><td><span>{e['legenda']}</span></td></tr>")
            f.write(f"<tr><td class='title'>Contato (JID/Phone)</td><td>{e['phone']}</td></tr>")
            f.write(f"<tr><td class='title'>Nome Original</td><td>{e['media_name']}</td></tr>")
            f.write(f"<tr><td class='title'>Status Chave</td><td>{e['key_status']}</td></tr>")
            f.write(f"<tr><td class='title'>Data do Registro</td><td>{e['date_human']}</td></tr>")
            f.write(f"<tr><td class='title'>Fluxo</td><td>{e['origin']}</td></tr>")
            f.write(f"<tr><td class='title'>Chave Vinculada (Hex)</td><td><code>{e['key_material']}</code></td></tr>")
            f.write(f"<tr><td class='title'>URL Completa Origem</td><td><code>{e['url_bruta']}</code></td></tr>")
            f.write("</table></div>")
            
        f.write("</body></html>")

    try:
        webbrowser.open(f"file:///{os.path.abspath(report_path)}", new=2)
    except Exception as browser_err:
        pass

# ===================== INTERFACE GRÁFICA UNIFICADA =====================

class AppForense(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Avilla Forensic - Target Media Recovery Tool v12.4 [SUPER-VERBOSE PARALELO]")
        self.geometry("950x700")
        self.configure(bg="#f4f6f9")

        self.db_path  = tk.StringVar()
        self.out_dir  = tk.StringVar(value="C:/output_media_residual")
        self.limit    = tk.IntVar(value=50)
        self.ui_queue = queue.Queue()
        self.running  = False

        self.build_ui()
        self.check_queue_loop()

    def build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except:
            pass

        # Frame de Configurações
        frame_config = ttk.LabelFrame(self, text=" Configurações de Auditoria ")
        frame_config.pack(fill="x", padx=15, pady=10)

        ttk.Label(frame_config, text="Banco msgstore.db:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame_config, textvariable=self.db_path, width=65).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(frame_config, text="Procurar...", command=self.browse_db).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(frame_config, text="Diretório de Saída:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame_config, textvariable=self.out_dir, width=65).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(frame_config, text="Alterar...", command=self.browse_out).grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(frame_config, text="Limite de Registros:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame_config, textvariable=self.limit, width=15).grid(row=2, column=1, sticky="w", padx=5, pady=5)

        self.btn_run = ttk.Button(self, text="▶ Executar Processamento Concorrente e Gerar Laudo", command=self.start_process)
        self.btn_run.pack(fill="x", padx=15, pady=5)

        # Barra de Progresso e ListBox (Para arquivos extraídos)
        frame_progresso = ttk.Frame(self)
        frame_progresso.pack(fill="x", padx=15, pady=5)
        
        self.progress = ttk.Progressbar(frame_progresso, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(0, 5))
        
        self.lbl_status = ttk.Label(frame_progresso, text="Registros Processados: 0", font=("Segoe UI", 10, "bold"))
        self.lbl_status.pack(anchor="w")

        self.list_extraidos = tk.Listbox(frame_progresso, height=4, background="#fdfdfd", font=("Segoe UI", 9))
        self.list_extraidos.pack(fill="x", pady=5)

        # Terminal Integrado (Substitui a janela secundária do Super Verbose)
        frame_log = ttk.LabelFrame(self, text=" Terminal Forense de Rede [SUPER-VERBOSE] ")
        frame_log.pack(fill="both", expand=True, padx=15, pady=10)

        self.txt_log = tk.Text(
            frame_log, bg="#0a0f1d", fg="#00e5ff",
            font=("Consolas", 9), wrap="none"
        )
        self.txt_log.pack(fill="both", expand=True, side="left", padx=5, pady=5)

        scrolly = ttk.Scrollbar(frame_log, orient="vertical", command=self.txt_log.yview)
        scrolly.pack(fill="y", side="right")
        self.txt_log.configure(yscrollcommand=scrolly.set)

        # Tags de Cor do Terminal
        self.txt_log.tag_config("cyan",   foreground="#00e5ff")
        self.txt_log.tag_config("red",    foreground="#ff5252")
        self.txt_log.tag_config("green",  foreground="#69f0ae")
        self.txt_log.tag_config("white",  foreground="#ffffff")
        self.txt_log.tag_config("yellow", foreground="#ffd600")
        self.txt_log.tag_config("gray",   foreground="#8b949e")

    def browse_db(self):
        f = filedialog.askopenfilename(filetypes=[("SQLite Databases", "*.db;*.sqlite"), ("All Files", "*.*")])
        if f: self.db_path.set(f)

    def browse_out(self):
        d = filedialog.askdirectory()
        if d: self.out_dir.set(d)

    def log(self, text, tag="white"):
        self.txt_log.insert(tk.END, text + "\n", tag)
        self.txt_log.see(tk.END)

    def start_process(self):
        if self.running: return
        if not self.db_path.get() or not self.out_dir.get():
            messagebox.showerror("Erro de Configuração", "Selecione o banco de dados e a pasta de saída.")
            return

        self.running = True
        self.btn_run.config(state="disabled")
        self.txt_log.delete("1.0", tk.END)
        self.list_extraidos.delete(0, tk.END)
        self.progress["value"] = 0
        self.lbl_status.config(text="Registros Processados: 0")

        t = threading.Thread(
            target=process_database_worker,
            args=(self.db_path.get(), self.out_dir.get(), self.limit.get(), self.ui_queue),
            daemon=True
        )
        t.start()

    def check_queue_loop(self):
        while not self.ui_queue.empty():
            try:
                task = self.ui_queue.get_nowait()
                action = task.get("action")
                data   = task.get("data", {})

                if action == "log":
                    self.log(data.get("msg"), data.get("color_mode", "white"))
                elif action == "log_block":
                    for text, tag in data.get("logs", []):
                        self.log(text, tag)
                elif action == "set_max_progress":
                    self.progress["maximum"] = data.get("max_val", 100)
                elif action == "update_progress":
                    val = data.get("value", 0)
                    self.progress["value"] = val
                    self.lbl_status.config(text=f"Registros Processados: {val}")
                elif action == "add_list":
                    prefix = "❌ " if data.get("is_error") else "✅ "
                    self.list_extraidos.insert(tk.END, prefix + data.get("text"))
                    self.list_extraidos.see(tk.END)
                elif action == "finish":
                    self.running = False
                    self.btn_run.config(state="normal")
                    self.log("\n[+] Auditoria Forense finalizada.", "green")
                    messagebox.showinfo("Auditoria Concluída", f"Laudo técnico compilado e aberto.\nDiretório: {data.get('report_dir')}")
            except:
                pass
        self.after(100, self.check_queue_loop)

if __name__ == "__main__":
    app = AppForense()
    app.mainloop()
