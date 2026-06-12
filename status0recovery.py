# -*- coding: utf-8 -*-
#!/usr/bin/env python3

import sqlite3
import os
import requests
import hashlib
import hmac
import threading
import webbrowser
from Crypto.Cipher import AES
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog

# ===================== CRYPTO =====================

appInfo = {
    "image": b"WhatsApp Image Keys",
    "video": b"WhatsApp Video Keys",
    "audio": b"WhatsApp Audio Keys",
    "document": b"WhatsApp Document Keys",
}

def HKDF(key,length,appInfo=b""):
    key = hmac.new(b"\0"*32,key,hashlib.sha256).digest()
    keyStream=b""
    keyBlock=b""
    blockIndex=1

    while len(keyStream)<length:
        keyBlock=hmac.new(
            key,
            msg=keyBlock+appInfo+bytes([blockIndex]),
            digestmod=hashlib.sha256
        ).digest()

        keyStream+=keyBlock
        blockIndex+=1

    return keyStream[:length]


def AESUnpad(s):
    return s[:-s[-1]]


def AESDecrypt(key,ciphertext,iv):
    cipher=AES.new(key,AES.MODE_CBC,iv)
    plaintext=cipher.decrypt(ciphertext)
    return AESUnpad(plaintext)


def decrypt_file(enc_path,mediaKey,mediaType,output_path):

    mediaKeyExpanded=HKDF(mediaKey,112,appInfo[mediaType])

    iv=mediaKeyExpanded[:16]
    cipherKey=mediaKeyExpanded[16:48]

    with open(enc_path,"rb") as f:
        mediaData=f.read()

    file=mediaData[:-10]

    data=AESDecrypt(cipherKey,file,iv)

    with open(output_path,'wb') as f:
        f.write(data)

# ===================== AUX =====================

def extract_media_key(blob):
    if not blob:
        return None
    if blob[0]==0x0a and blob[1]==0x20:
        return blob[2:34]
    return blob[:32]


def detect_media_type(file_path,mime):

    if mime:
        if "image" in mime:
            return "image"
        if "video" in mime:
            return "video"
        if "audio" in mime:
            return "audio"

    if file_path:
        ext=file_path.split(".")[-1].lower()

        if ext in ["jpg","jpeg","png","webp"]:
            return "image"

        if ext in ["mp4","3gp"]:
            return "video"

        if ext in ["opus","ogg","aac","wav"]:
            return "audio"

    return "document"


def convert_android_date(ts):
    try:
        return datetime.fromtimestamp(int(ts)/1000).strftime("%d/%m/%Y %H:%M:%S")
    except:
        return "Invalid Date"

# ===================== CORE =====================

def process_database(db_path,output_dir,limit_param,gui):

    conn=sqlite3.connect(db_path)
    cursor=conn.cursor()

    # Query atualizada para refletir a estrutura de tabelas moderna (tabela 'message' no singular)
    # e contornando a ausência da coluna 'local_path' ou 'file_path' na message_media
    query = """
        SELECT
            m._id,
            mm.message_url,
            mm.media_key,
            mm.file_size,
            mm.mime_type,
            m.timestamp,
            m.from_me,
            m.message_type,
            jl.raw_string AS lid,
            CASE
                WHEN jr.raw_string IS NOT NULL THEN jr.raw_string
                ELSE jl.raw_string
            END AS phone
        FROM message_media mm
        JOIN message m ON m._id = mm.message_row_id
        LEFT JOIN chat c ON c._id = m.chat_row_id
        LEFT JOIN jid jl ON jl._id = c.jid_row_id
        LEFT JOIN jid_map jm ON jm.lid_row_id = jl._id
        LEFT JOIN jid jr ON jr._id = jm.jid_row_id
        WHERE mm.message_url IS NOT NULL
        ORDER BY m.timestamp DESC
    """

    if limit_param.lower()!="all":
        query+=f" LIMIT {limit_param}"

    cursor.execute(query)
    rows=cursor.fetchall()

    gui.progress["maximum"]=len(rows)
    report_entries=[]

    enc_folder=os.path.join(output_dir,"_enc")
    os.makedirs(enc_folder,exist_ok=True)

    for i,row in enumerate(rows):

        (id_row,url,key_blob,size,mime_type,
        timestamp,origin,msgtype,lid,phone)=row

        if not url:
            continue

        # Extração segura da chave binária tratada
        if key_blob:
            media_key=extract_media_key(key_blob)
        else:
            continue

        if not media_key:
            continue

        # Geração dinâmica e determinística da árvore de diretórios baseada nos tipos reais
        if msgtype == 42 or (mime_type and "image" in mime_type):
            file_path=f"Media/WhatsApp Images/recuperado_{id_row}.jpg"
        elif msgtype == 43 or (mime_type and "video" in mime_type):
            file_path=f"Media/WhatsApp Video/recuperado_{id_row}.mp4"
        elif msgtype == 82 or (mime_type and "audio" in mime_type):
            file_path=f"Media/WhatsApp Voice Notes/recuperado_{id_row}.opus"
        else:
            file_path=f"Media/WhatsApp Documents/doc_{id_row}.bin"

        gui.progress["value"]=i+1
        gui.root.update_idletasks()

        enc_path=os.path.join(enc_folder,str(id_row)+".enc")

        try:
            r=requests.get(url,timeout=30)
            if r.status_code!=200:
                continue
            with open(enc_path,"wb") as f:
                f.write(r.content)
        except:
            continue

        media_type=detect_media_type(file_path,mime_type)
        output_file=os.path.join(output_dir,file_path)
        os.makedirs(os.path.dirname(output_file),exist_ok=True)

        try:
            decrypt_file(enc_path,media_key,media_type,output_file)
        except Exception as e:
            print(f"Falha ao descriptografar ID {id_row}: {e}")
            continue

        gui.files_list.insert(tk.END,output_file)
        gui.files_list.yview_moveto(1)

        gui.media_count+=1
        gui.media_label.config(text=f"Mídias recuperadas: {gui.media_count}")

        if msgtype in (42,43,82):
            gui.unique_list.insert(tk.END,output_file)
            gui.unique_list.yview_moveto(1)
            gui.unique_count+=1
            gui.unique_label.config(text=f"Visualização única: {gui.unique_count}")

        report_entries.append({
            "id":id_row,
            "lid":lid,
            "phone":phone,
            "msg_type":msgtype,
            "url":url,
            "key":media_key.hex(),
            "path":output_file,
            "date_raw":timestamp,
            "date_human":convert_android_date(timestamp),
            "size":size,
            "origin":"Enviada" if origin==1 else "Recebida"
        })

    conn.close()
    report_path=generate_report(report_entries,output_dir)
    webbrowser.open(report_path)

# ===================== HTML =====================

def generate_report(entries,output_dir):

    report_path=os.path.join(output_dir,"report.html")

    with open(report_path,"w",encoding="utf-8") as f:

        f.write("<html><head><meta charset='utf-8'>")
        f.write("<title>WhatsApp Android Media Report</title></head><body>")
        f.write("<h1>WhatsApp Android Media Extraction</h1>")

        for e in entries:

            html_path=os.path.relpath(e["path"],output_dir).replace("\\","/")
            f.write("<div style='margin-bottom:25px;'>")

            if e["msg_type"] in (42,43,82):
                f.write("<span style='color:red;font-weight:bold;'>VISUALIZAÇÃO ÚNICA RECUPERADA</span><br>")

            f.write(f"LID: {e['lid']}<br>")
            f.write(f"Telefone: {e['phone']}<br>")
            f.write(f"ID: {e['id']}<br>")
            f.write(f"Data Raw: {e['date_raw']}<br>")
            f.write(f"Data Humana: {e['date_human']}<br>")
            f.write(f"Origem: {e['origin']}<br>")
            f.write(f"Tamanho: {e['size']} bytes<br>")
            f.write(f"URL: <a href='{e['url']}' target='_blank'>{e['url']}</a><br>")
            f.write(f"MediaKey: {e['key']}<br>")
            f.write(f"Arquivo: <a href='{html_path}' target='_blank'>{html_path}</a><br>")
            f.write("</div><hr>")

        f.write("</body></html>")

    return report_path

# ===================== GUI =====================

class App:

    def __init__(self,root):

        self.root=root
        root.title("Avilla WhatsApp Android Media Recovery")
        root.state("zoomed")
        root.option_add("*Font",("Segoe UI",11))

        frame=ttk.Frame(root,padding=10)
        frame.pack(fill="both",expand=True)
        frame.columnconfigure(1,weight=1)

        ttk.Label(frame,text="Banco de dados").grid(row=0,column=0,sticky="w")

        self.db_entry=ttk.Entry(frame)
        self.db_entry.grid(row=0,column=1,sticky="ew")

        ttk.Button(frame,text="Selecionar",command=self.select_db).grid(row=0,column=2)
        ttk.Label(frame,text="Saída").grid(row=1,column=0,sticky="w")

        self.out_entry=ttk.Entry(frame)
        self.out_entry.insert(0,"output_media")
        self.out_entry.grid(row=1,column=1,sticky="ew")

        ttk.Button(frame,text="Alterar",command=self.select_out).grid(row=1,column=2)
        ttk.Label(frame,text="Limite").grid(row=2,column=0)

        self.limit_entry=ttk.Entry(frame,width=10)
        self.limit_entry.insert(0,"100")
        self.limit_entry.grid(row=2,column=1,sticky="w")

        ttk.Button(frame,text="Executar",command=self.run).grid(row=2,column=2)

        self.progress=ttk.Progressbar(frame)
        self.progress.grid(row=3,column=0,columnspan=3,sticky="ew",pady=10)

        self.media_count=0
        self.unique_count=0

        self.media_label=ttk.Label(frame,text="Mídias recuperadas: 0")
        self.media_label.grid(row=4,column=0,sticky="w")

        self.unique_label=ttk.Label(frame,text="Visualização única: 0")
        self.unique_label.grid(row=4,column=1,sticky="w",padx=40)

        ttk.Label(frame,text="Arquivos recuperados").grid(row=5,column=0,sticky="w")

        self.files_list=tk.Listbox(frame)
        self.files_list.grid(row=6,column=0,columnspan=3,sticky="nsew")

        ttk.Label(frame,text="Visualização única").grid(row=7,column=0,sticky="w")

        self.unique_list=tk.Listbox(frame)
        self.unique_list.grid(row=8,column=0,columnspan=3,sticky="nsew")

        frame.rowconfigure(6,weight=1)
        frame.rowconfigure(8,weight=1)

        self.files_list.bind("<Double-Button-1>",self.open_media)
        self.unique_list.bind("<Double-Button-1>",self.open_media)

    def open_media(self,event):
        widget=event.widget
        selection=widget.curselection()
        if selection:
            path=widget.get(selection[0])
            os.startfile(os.path.abspath(path))

    def select_db(self):
        path=filedialog.askopenfilename()
        self.db_entry.delete(0,tk.END)
        self.db_entry.insert(0,path)

    def select_out(self):
        path=filedialog.askdirectory()
        self.out_entry.delete(0,tk.END)
        self.out_entry.insert(0,path)

    def run(self):
        db=self.db_entry.get()
        out=self.out_entry.get()
        limit=self.limit_entry.get()
        threading.Thread(target=process_database,args=(db,out,limit,self)).start()

# ===================== START =====================

if __name__=="__main__":
    root=tk.Tk()
    app=App(root)
    root.mainloop()
