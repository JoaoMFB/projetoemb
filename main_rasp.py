import cv2
import collections
import mediapipe as mp
import time

# --- Parâmetros de Configuração ---
CAMERA_INDEX = 0 
# Taxa de quadros: Reduzir para garantir estabilidade na Pi.
FPS = 15 
BUFFER_DURATION_SECONDS = 20
MAX_FRAMES = int(FPS * BUFFER_DURATION_SECONDS)
OUTPUT_FILENAME = f"lance_capturado_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
# Codec: 'mp4v' ou 'XVID' são opções comuns para a arquitetura ARM.
FOURCC_CODEC = 'mp4v' 

# Variável de Controle
GESTO_X_DETECTADO = False

# Criação do buffer circular (deque)
frame_buffer = collections.deque(maxlen=MAX_FRAMES)

# Configuração do MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    model_complexity=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils


def check_x_gesture(landmarks, frame_width):
    """
    Verifica o gesto 'X' com braços cruzados (Cotovelo vs. Pulso).
    """
    if not landmarks:
        return False
        
    # Posições X normalizadas (0 a 1)
    left_elbow_x = landmarks.landmark[mp_pose.PoseLandmark.LEFT_ELBOW].x 
    left_wrist_x = landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST].x
    right_elbow_x = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_ELBOW].x
    right_wrist_x = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST].x
    
    # Critério do Braço Direito: Cotovelo (X) à esquerda do Pulso (Y)
    right_arm_crossed = right_elbow_x < right_wrist_x
    
    # Critério do Braço Esquerdo: Cotovelo (X) à direita do Pulso (Y)
    left_arm_crossed = left_elbow_x > left_wrist_x
    
    # Gesto 'X' se ambos estiverem cruzados
    return right_arm_crossed and left_arm_crossed


def save_buffer_to_video(buffer, output_file, fps, frame_size):
    """Salva todos os frames do buffer em um arquivo de vídeo."""
    print(f"\n--- SALVANDO VÍDEO: {output_file} ---")
    
    fourcc = cv2.VideoWriter_fourcc(*FOURCC_CODEC) 
    out = cv2.VideoWriter(output_file, fourcc, fps, frame_size)
    
    if not out.isOpened():
        print(f"ERRO: Não foi possível inicializar VideoWriter. Tente mudar o codec (FOURCC_CODEC='XVID').")
        return False
    
    for frame in buffer:
        out.write(frame)
        
    out.release()
    print(f"Vídeo salvo com sucesso! Duração: {len(buffer)/fps:.2f} segundos.")
    return True


def run_capture_loop():
    """Loop principal de captura, processamento e salvamento na Raspberry Pi."""
    global GESTO_X_DETECTADO
    
    # --- MUDANÇA CRUCIAL PARA RASPBERRY PI ---
    # Usando CAP_V4L2 para forçar o driver de vídeo no Linux embarcado.
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2) 
    
    if not cap.isOpened():
        print(f"ERRO: Não foi possível iniciar o stream da câmera no índice {CAMERA_INDEX} com CAP_V4L2.")
        print("Verifique se a câmera está habilitada no raspi-config e se o driver está ativo.")
        return

    # Otimização: Forçar Resolução Baixa (640x480) para melhor desempenho de detecção
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, FPS)
    
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_size = (frame_w, frame_h)
    
    print(f"RPI Capturando a {frame_w}x{frame_h} | Buffer: {BUFFER_DURATION_SECONDS}s.")
    
    try:
        while not GESTO_X_DETECTADO:
            ret, frame = cap.read()
            
            if not ret:
                print("ERRO: Falha ao ler o frame.")
                break
            
            # MediaPipe requer RGB, mas OpenCV retorna BGR
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Para otimizar o MediaPipe na Pi, reduza a imagem para processamento
            # A redução deve ser feita APENAS para o processamento de pose
            # frame_pequeno = cv2.resize(rgb_frame, (320, 240))
            
            # O processamento da pose é feito na imagem em RGB
            results = pose.process(rgb_frame)
            
            if results.pose_landmarks:
                mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                
                if check_x_gesture(results.pose_landmarks, frame_w):
                    print("\n>>> GESTO 'X' VÁLIDO DETECTADO! SALVANDO! <<<")
                    GESTO_X_DETECTADO = True
            
            frame_buffer.append(frame)
            
            # Na RPi OS Lite (sem ambiente gráfico), esta linha deve ser removida ou comentada!
            # cv2.imshow('Captura Inteligente - Gesto X (Pose)', frame)
            
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break
                
        if GESTO_X_DETECTADO:
            save_buffer_to_video(frame_buffer, OUTPUT_FILENAME, FPS, frame_size)
            
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
        
    finally:
        cap.release()
        # cv2.destroyAllWindows() # Remover em ambiente sem display
        pose.close()
        print("Recursos liberados.")


if __name__ == "__main__":
    run_capture_loop()