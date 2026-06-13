import struct
import string
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

def gerar_hex_dump(dados):
    """Gera um dump hexadecimal estruturado com representação em texto legível."""
    linhas = []
    for i in range(0, len(dados), 16):
        bloco = dados[i:i+16]
        hex_part = " ".join(f"{b:02X}" for b in bloco)
        hex_part = hex_part.ljust(47) # Alinhamento da coluna hex
        
        # Representação textual (substitui caracteres não imprimíveis por ponto)
        text_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in bloco)
        linhas.append(f"        {i:04X}  {hex_part}  |{text_part}|")
    return "\n".join(linhas)

def analisar_freeblocks_sqlite(caminho_banco, area_texto, tamanho_pagina=4096):
    try:
        with open(caminho_banco, 'rb') as f:
            dados_banco = f.read()
    except Exception as e:
        messagebox.showerror("Erro de Leitura", f"Não foi possível abrir o arquivo:\n{e}")
        return

    if dados_banco[:15] != b'SQLite format 3':
        area_texto.insert(tk.END, "[ERRO CRÍTICO] Arquivo inválido ou criptografado!\n")
        return

    total_paginas = len(dados_banco) // tamanho_pagina
    area_texto.insert(tk.END, f"[*] Arquivo SQLite válido detectado.\n")
    area_texto.insert(tk.END, f"[*] Analisando {total_paginas} páginas...\n")
    area_texto.insert(tk.END, "="*70 + "\n\n")
    area_texto.update_idletasks()

    blocos_encontrados = 0

    for num_pagina in range(1, total_paginas + 1):
        offset_pagina = (num_pagina - 1) * tamanho_pagina
        offset_cabeçalho = offset_pagina + 100 if num_pagina == 1 else offset_pagina
        
        if offset_cabeçalho >= len(dados_banco):
            break
            
        tipo_pagina = dados_banco[offset_cabeçalho]
        
        if tipo_pagina == 0x0D:
            primeiro_freeblock_offset = struct.unpack('>H', dados_banco[offset_cabeçalho + 1 : offset_cabeçalho + 3])[0]
            
            if primeiro_freeblock_offset != 0:
                proximo_offset = primeiro_freeblock_offset
                
                while proximo_offset != 0:
                    posicao_absoluta = offset_pagina + proximo_offset
                    
                    if proximo_offset + 4 > tamanho_pagina or posicao_absoluta + 4 > len(dados_banco):
                        break
                        
                    ponteiro_proximo, tamanho_bloco = struct.unpack('>HH', dados_banco[posicao_absoluta : posicao_absoluta + 4])
                    
                    inicio_payload = posicao_absoluta + 4
                    fim_payload = posicao_absoluta + tamanho_bloco
                    
                    if tamanho_bloco <= 4 or fim_payload > len(dados_banco):
                        break
                        
                    dados_residuais = dados_banco[inicio_payload:fim_payload]
                    
                    # Exibe informações do bloco e o Hex Dump
                    area_texto.insert(tk.END, f"[+] Página {num_pagina} | Freeblock em Offset {proximo_offset} | Tamanho: {tamanho_bloco} bytes\n")
                    area_texto.insert(tk.END, gerar_hex_dump(dados_residuais) + "\n")
                    area_texto.insert(tk.END, "-" * 70 + "\n")
                    
                    blocos_encontrados += 1
                    proximo_offset = ponteiro_proximo
                area_texto.see(tk.END)
                area_texto.update_idletasks()

    area_texto.insert(tk.END, f"\n[V] Varredura Concluída. Total de Freeblocks: {blocos_encontrados}\n")
    area_texto.see(tk.END)

def selecionar_arquivo():
    caminho = filedialog.askopenfilename(
        title="Selecionar Banco de Dados do WhatsApp",
        filetypes=[("Arquivos SQLite/DB", "*.db"), ("Todos os arquivos", "*.*")]
    )
    if caminho:
        lbl_caminho.config(text=f"Arquivo: {caminho}")
        txt_resultado.delete('1.0', tk.END)
        analisar_freeblocks_sqlite(caminho, txt_resultado)

# Interface Gráfica
janela = tk.Tk()
janela.title("Visualizador Hexadecimal de Freeblocks")
janela.geometry("900x650")

btn_selecionar = tk.Button(janela, text="Selecionar Banco de Dados (msgstore.db)", command=selecionar_arquivo, bg="#4CAF50", fg="white", font=("Arial", 11, "bold"))
btn_selecionar.pack(pady=15)

lbl_caminho = tk.Label(janela, text="Nenhum arquivo selecionado", fg="gray", font=("Arial", 9, "italic"))
lbl_caminho.pack(pady=5)

txt_resultado = scrolledtext.ScrolledText(janela, width=105, height=28, font=("Consolas", 9))
txt_resultado.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

janela.mainloop()
