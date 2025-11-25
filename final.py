import cv2
import collections
import numpy as np
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

#configuracoes principais do sistema
FPS = 30
BUFFER_DURATION_SECONDS = 15
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

#configuracoes de email
EMAIL_ORIGEM = "embarcadosp@gmail.com"
EMAIL_SENHA = "xzta jwoy hxsv lmiq"
EMAIL_DESTINO = "jfbattaglini@gmail.com"

#buffer circular para armazenar frames
frame_buffer = collections.deque(maxlen=int(FPS * BUFFER_DURATION_SECONDS))

def save_buffer_to_video(buffer, output_file, fps):
    #salva o buffer de frames em um arquivo de video
    if not buffer:
        print("Buffer vazio, nada para salvar")
        return False
    
    height, width = buffer[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_file, fourcc, fps, (width, height))
    
    if not out.isOpened():
        print(f"Erro ao criar video {output_file}")
        return False
    
    for frame in buffer:
        out.write(frame)
    
    out.release()
    duracao = len(buffer) / fps
    print(f"Video salvo: {output_file} ({duracao:.2f}s)")
    return True

def enviar_email(arquivo_video):
    #envia o arquivo de video por email usando smtp
    try:
        print("Preparando email...")
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ORIGEM
        msg['To'] = EMAIL_DESTINO
        msg['Subject'] = f"Video Capturado - {time.strftime('%d/%m/%Y %H:%M:%S')}"
        
        corpo = f"""
Ola!

Um novo video foi capturado pelo sistema de monitoramento.

Detalhes:
- Data/Hora: {time.strftime('%d/%m/%Y as %H:%M:%S')}
- Duracao: {BUFFER_DURATION_SECONDS} segundos
- Arquivo: {arquivo_video}

Att,
Sistema de Captura Raspberry Pi
        """
        
        msg.attach(MIMEText(corpo, 'plain'))
        
        with open(arquivo_video, 'rb') as arquivo:
            parte = MIMEBase('application', 'octet-stream')
            parte.set_payload(arquivo.read())
            encoders.encode_base64(parte)
            parte.add_header('Content-Disposition', f'attachment; filename={arquivo_video}')
            msg.attach(parte)
        
        print("Conectando ao servidor SMTP...")
        servidor = smtplib.SMTP('smtp.gmail.com', 587)
        servidor.starttls()
        servidor.login(EMAIL_ORIGEM, EMAIL_SENHA)
        
        texto = msg.as_string()
        servidor.sendmail(EMAIL_ORIGEM, EMAIL_DESTINO, texto)
        servidor.quit()
        
        print("Email enviado com sucesso!")
        return True
        
    except Exception as e:
        print(f"Erro ao enviar email: {e}")
        print("Dica: verificar configuracao de senhas de app no Gmail")
        return False

def run_capture_loop():
    #executa o loop principal de captura da camera
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Erro: nao foi possivel abrir a camera")
        print("Tentando forcar backend V4L2...")
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        
        if not cap.isOpened():
            print("Falha ao abrir camera. Verifique a conexao.")
            return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FPS)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    
    real_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    real_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    real_fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    print("============================================================")
    print("SISTEMA DE CAPTURA INTELIGENTE - RASPBERRY PI 3")
    print("============================================================")
    print(f"Resolucao: {real_width}x{real_height} @ {real_fps}fps")
    print(f"Buffer: {frame_buffer.maxlen} frames ({BUFFER_DURATION_SECONDS}s)")
    print(f"Email destino: {EMAIL_DESTINO}")
    print("------------------------------------------------------------")
    print("Pressione ENTER para salvar video e enviar email")
    print("Pressione 'q' para sair")
    print("============================================================")
    
    print("Aguardando camera estabilizar...")
    for _ in range(30):
        cap.read()
    
    print("Camera pronta! Iniciando captura...\n")
    
    try:
        frame_count = 0
        while True:
            ret, frame = cap.read()
            
            if not ret:
                print("Falha ao capturar frame")
                time.sleep(0.1)
                continue
            
            frame_count += 1
            frame_buffer.append(frame.copy())
            
            buffer_pct = int((len(frame_buffer) / frame_buffer.maxlen) * 100)
            cv2.putText(frame, f"Buffer: {len(frame_buffer)}/{frame_buffer.maxlen} ({buffer_pct}%)",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, "Pressione ENTER para salvar",
                       (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(frame, f"Frames: {frame_count}",
                       (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            cv2.imshow("Captura Inteligente - Raspberry Pi", frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == 13 or key == ord('\r') or key == ord('\n'):
                print("\n============================================================")
                print("CAPTURA ACIONADA!")
                print("============================================================")
                
                output_file = f"lance_capturado_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
                
                if save_buffer_to_video(list(frame_buffer), output_file, real_fps):
                    enviar_email(output_file)
                
                print("============================================================")
                print("Processo concluido! Aguardando proxima captura...")
                print("============================================================\n")
            
            elif key == ord('q'):
                print("\nEncerrando captura...")
                break
    
    except KeyboardInterrupt:
        print("\nCaptura interrompida pelo usuario")
    
    except Exception as e:
        print(f"\nErro: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Recursos liberados com sucesso")
        print("Ate logo!")

if __name__ == "__main__":
    run_capture_loop()