# viewoncerecovery
Trabalho de conclusão de curso da faculdade de Tecnologia de Segurança em informação
<br></br>
Por : Filipe Augusto Pereira Damaceno e Reno

Reno: Um agradecimento à minha mãe que nunca desistiu da minha capacidade, e aos verdadeiros amigos que me auxiliaram nessa jornada contra a famosa, e querida síndrome do impostor. Um salve especial ao engenheiro Paulo da Petrobrás, e psicóloga Thais, ao poeta, cantor e palhaço Sergio Christo vulgo V3sp3ro que espalha esperança em suas canções e atos, ao programador Rafael Misael, ao Dr. Pedro Lourenço, ao amigo de longas datas e grafiteiro Rato,aos mestres que me ajudaram a educar minha mediunidade: Arnaldo, Carlos Alberto, Katia, Ana, Julio,Elaine, e todos amigos do CEFE/CEIR, à Julia Horfig, ao camarada Victor Cavalcante, e todos e todas que sempre fortaleceram minha caminhada, minha eterna gratidão!

Sejam bem vindos
Aqui vcs vão encontrar a pesquisa que estamos realizando para recuperar mensagens de visualização Única do Whatsapp. O script disponível por enquanto é apenas para android, na versão antiga criada por Daniel Avilla e Ibsen Maciel, mas as modificações podem ser feitas que irão encontrar as melhores formas para recuperação de mídias para outros dispositivos.

Apesar das ameaças de pessoas que não entendem o que faço, aqui do prédio, seguimos estudando e colocando em prática o conhecimento aberto.



O script atualizado vou postar no dia 02/07, aqui vcs podem ver uma prévia:
<img width="1301" height="495" alt="image" src="https://github.com/user-attachments/assets/3862e4d6-6f28-43da-ba32-f56148d6f80a" />

 O atualizado possui atualizações de recuperação de legenda de mídia de visualização única, independente do status, características se a mensagem foi enviada a um ou vários contatos, e ainda estou estudando, o que faz ela realmente se tornar state1 o grande problema atual que muitos ainda não conseguem recuperar!
<img width="1282" height="343" alt="image" src="https://github.com/user-attachments/assets/1016a8bb-2b32-4e3b-adda-51b12aa9bc5d" />

Para inicio de conversa tudo isso só foi possivel por causa de uma pessoa que tb deve ter passado por alguns bocados, o perito e investigador Daniel Avilla, que forneceu a ferramenta dele de forma gratuita. Um salve aos mestres desconhecidos, que ajudaram ele a criar isso tambem, segue o trampo dele lá, ele é o real autor dessas ferramentas, nós apenas estamos ajudando.
https://github.com/AvillaDaniel/AvillaForensics
Valeu professor!

Seguimos.
<img width="960" height="540" alt="Apresentação - Técnica" src="https://github.com/user-attachments/assets/ddddcf1e-f8bf-407b-849f-94d739f506d2" />



Antes de começarmos, essa nota técnica e ética faz todo sentido de divulgar, pra não nos metermos em problemas:
<img width="960" height="540" alt="Apresentação -  Empresa" src="https://github.com/user-attachments/assets/2e29d5d5-69f3-4cb6-ad47-83784bfdcb55" />

Sobre o Avilla Forensics: 
<img width="960" height="540" alt="Apresentação -  Empresa (1)" src="https://github.com/user-attachments/assets/123c4fca-837b-4e87-bdf9-d66e9eb3c636" />
Noticias do Avilla:
<img width="960" height="540" alt="Apresentação -  Empresa (2)" src="https://github.com/user-attachments/assets/d0579b78-2dca-4db2-a83e-a8b6ced8d836" />
Nossa contribuição:
<img width="960" height="540" alt="Apresentação -  Empresa (3)" src="https://github.com/user-attachments/assets/e5a02fc7-a871-4042-8e6f-45f8a1375d09" />

 Metodologia de Extração e aquisição de msgstore.db descriptografado:
<img width="960" height="540" alt="Apresentação - Técnica (3)" src="https://github.com/user-attachments/assets/4d4f5c79-464b-4043-9c21-0fe10cf0d3f9" />

Termos necessários de compreensão de estrutura criptográfica do Whatsapp:
<img width="960" height="540" alt="Apresentação - Técnica (4)" src="https://github.com/user-attachments/assets/bbfd49d5-9c50-4199-9190-d1484a941455" />

Da anatomia do link  da CDN do Whatsapp:
<img width="960" height="540" alt="Apresentação - Técnica (5)" src="https://github.com/user-attachments/assets/ee0750fa-af8f-4880-89ef-f773e1c443d2" />

 Visualização e explicação:
<img width="960" height="540" alt="Apresentação - Técnica (6)" src="https://github.com/user-attachments/assets/2321cefd-5886-409a-8912-128a50da009e" />

Termos necessários de compreensão:
<img width="960" height="540" alt="Apresentação - Técnica (7)" src="https://github.com/user-attachments/assets/088af6d0-a162-4fa1-9c90-833b0a8f49e1" />

Teste strings sem fins maliciosos:
<img width="960" height="540" alt="Apresentação - Técnica (8)" src="https://github.com/user-attachments/assets/ae2c110a-1dd5-44fc-9002-b27bbb76d812" />

Validação de nome real de mídia, para defesa não desvalidar:

<img width="960" height="540" alt="Apresentação - Técnica (9)" src="https://github.com/user-attachments/assets/1f6ea916-c676-4b0f-aa7b-dea726699c8f" />

Validação de Dados:
<img width="960" height="540" alt="Apresentação - Técnica (11)" src="https://github.com/user-attachments/assets/8adca028-cf36-4833-acab-62fb3815ad64" />
<img width="960" height="540" alt="Apresentação - Técnica (10)" src="https://github.com/user-attachments/assets/eeba5953-33e5-4309-97f0-d2d636d63d8d" />

<img width="960" height="540" alt="Apresentação - Técnica (12)" src="https://github.com/user-attachments/assets/429c2ee0-2c65-42d7-bc1a-309d083379c4" />

Do path ter sido excluido dos áudios no Whatsapp Business:
<img width="960" height="540" alt="Apresentação - Técnica (13)" src="https://github.com/user-attachments/assets/3a14c6b0-01c6-4c56-b0b2-68d8b21ac515" />

<img width="960" height="540" alt="Apresentação - Técnica (14)" src="https://github.com/user-attachments/assets/81176a46-c2ef-4486-9979-24143f6d4d1b" />

Da explicação dos status de visualização única:
<img width="960" height="540" alt="Apresentação - Técnica (15)" src="https://github.com/user-attachments/assets/f38a6175-8886-4ebf-ab94-863aa96d456e" />

Validação de Media_Key de Status 0 :
<img width="960" height="540" alt="Slide18" src="https://github.com/user-attachments/assets/ff755d49-fd11-4e6f-89b0-661dbf70b64c" />

Validação no msgstore:
<img width="960" height="540" alt="Slide19" src="https://github.com/user-attachments/assets/8b93dc08-14d6-4afd-bcad-9b5ed8b7b03d" />

Status 0 para 1 sem key:
<img width="960" height="540" alt="Slide22" src="https://github.com/user-attachments/assets/cc29252c-1e7a-4070-adfd-676efd62948b" />


Da hipótese do status 1 :
<img width="960" height="540" alt="Apresentação - Técnica (16)" src="https://github.com/user-attachments/assets/4278a4d5-8101-4f7d-95ff-735edd7fbc1d" />

Mais informações do status 1: 
<img width="960" height="540" alt="Apresentação - Técnica (17)" src="https://github.com/user-attachments/assets/c94e853c-99be-4a00-a3bf-1c00480c26ae" />

Da hipótese do status 2 : 
<img width="960" height="540" alt="Apresentação - Técnica (18)" src="https://github.com/user-attachments/assets/e7e3f176-fed0-4900-8658-33b677f8b998" />

Da atualização do Script:
<img width="960" height="540" alt="Apresentação - Técnica (19)" src="https://github.com/user-attachments/assets/e7ff2354-d411-4175-a8e9-5c379779128e" />

Testes de auditoria:
<img width="960" height="540" alt="Apresentação - Técnica (20)" src="https://github.com/user-attachments/assets/4d96ceba-5a1f-4570-ac4c-907adf0f7d82" />

2 modelo de teste de auditoria:
<img width="960" height="540" alt="Apresentação - Técnica (21)" src="https://github.com/user-attachments/assets/79b4abdb-56e5-4706-a5f8-058d292201a7" />

Respostas conhecidas da CDN:
<img width="960" height="540" alt="Apresentação - Técnica (22)" src="https://github.com/user-attachments/assets/f9de3f31-47a3-41f7-919d-172b03af1377" />

Modo Auditoria - 3 Modelo:
<img width="960" height="540" alt="Apresentação - Técnica (23)" src="https://github.com/user-attachments/assets/5f1e4a84-f5c0-43cb-bbee-92f514710e24" />

<img width="960" height="540" alt="Apresentação - Técnica (24)" src="https://github.com/user-attachments/assets/730c6bdf-13c7-491f-8e47-26e9d887fb28" />

Novo método de validação de conexão:
<img width="960" height="540" alt="Apresentação - Técnica (25)" src="https://github.com/user-attachments/assets/478d941f-1ae0-4400-a20e-20b502429e47" />

Recuperação de legenda em mídias de visualização única:
<img width="960" height="540" alt="Apresentação - Técnica (26)" src="https://github.com/user-attachments/assets/1060db97-523e-4915-9ff9-434395415f04" />







 
Divulgado script final recovery1e0.py
