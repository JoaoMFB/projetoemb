import cv2
import collections
import mediapipe as mp
import time

CAMERA_INDEX = 0 
FPS = 30 
BUFFER_DURATION_SECONDS = 15 
MAX_FRAMES = int(FPS * BUFFER_DURATION_SECONDS)
OUTPUT_FILENAME = f"lance_capturado_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
FOURCC_CODEC = 'mp4v' 

# Variável de Controle
GESTO_X_DETECTADO = False

# Criação do buffer circular (deque)
frame_buffer = collections.deque(maxlen=MAX_FRAMES)

mp_hands = mp.solutions.hands

hands = mp_hands.Hands(
    model_complexity=1, 
    min_detection_confidence=0.5, 
    min_tracking_confidence=0.5,
    max_num_hands=2) 
mp_drawing = mp.solutions.drawing_utils


def check_x_gesture(hand_landmarks_list, frame_width, frame_height):
    """
    Verifica se o gesto 'X' foi realizado.
    """
    if len(hand_landmarks_list) < 2:
        return False
    
    # Ponto de referência: o pulso (landmark 0)
    wrist_a = hand_landmarks_list[0].landmark[mp_hands.HandLandmark.WRIST]
    wrist_b = hand_landmarks_list[1].landmark[mp_hands.HandLandmark.WRIST]

    # Converte coordenadas normalizadas (0 a 1) para pixels
    x_a = wrist_a.x * frame_width
    x_b = wrist_b.x * frame_width
    
    # Calcula a posição central das mãos
    center_a = wrist_a.x
    center_b = wrist_b.x

    # Lógica de Cruzamento:
    # Se a mão que está à direita (maior coordenada X) tiver seu pulso (ou palma) 
    # à esquerda do centro da mão que está à esquerda, há um cruzamento.
    
    # Margem de sobreposição para considerar o 'X'
    OVERLAP_THRESHOLD = 0.05 * frame_width # 
    
    if x_a < x_b:
        left_hand_x = x_a
        right_hand_x = x_b
    else:
        left_hand_x = x_b
        right_hand_x = x_a
        

    if abs(x_a - x_b) < OVERLAP_THRESHOLD:
        # Se os pulsos estão muito próximos, pode indicar que os braços estão cruzados
        # em frente ao corpo ou muito juntos, o que simula um 'X' para este protótipo.
        return True
    
    
    return False


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
    print("--------------------------------------\n")
    return True


def run_capture_loop():
    """Loop principal de captura, processamento e salvamento."""
    global GESTO_X_DETECTADO
    
    cap = cv2.VideoCapture(CAMERA_INDEX)
    
    if not cap.isOpened():
        print(f"ERRO: Não foi possível iniciar o stream da câmera no índice {CAMERA_INDEX}.")
        print("Verifique se a webcam está conectada.")
        return

    # Tenta definir a resolução e o FPS
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, FPS)
    
    # Obtém as dimensões reais
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_size = (frame_w, frame_h)
    
    print(f"Capturando a {frame_w}x{frame_h} | Buffer Máximo: {MAX_FRAMES} frames ({BUFFER_DURATION_SECONDS}s).")
    
    try:
        frame_count = 0
        while not GESTO_X_DETECTADO:
            ret, frame = cap.read()
            
            if not ret:
                print("ERRO: Falha ao ler o frame.")
                break
            
            frame_count += 1
            
            # 1. Processamento do Frame para Detecção
            # MediaPipe requer imagem em RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)
            
            # Lista para armazenar as landmarks das mãos detectadas
            hand_landmarks_list = []

            # 2. Desenho e Coleta de Dados
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Desenha as landmarks na tela (Visualização)
                    mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    
                    # Coleta as landmarks para a lógica do gesto
                    hand_landmarks_list.append(hand_landmarks)

                # 3. Lógica de Detecção do Gesto 'X'
                if len(hand_landmarks_list) >= 2:
                    if check_x_gesture(hand_landmarks_list, frame_w, frame_h):
                        print("\n>>> GESTO 'X' VÁLIDO DETECTADO! <<<")
                        GESTO_X_DETECTADO = True

            # 4. Adicionar ao Buffer Circular
            frame_buffer.append(frame)
            
            # 5. Exibir o Frame (Visualização)
            # Mostra o status do buffer no canto
            cv2.putText(frame, f"Buffer: {len(frame_buffer)}/{MAX_FRAMES}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow('Captura Inteligente - Gesto X', frame)

            # Para parar o loop, pressione 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                        
        # 6. Salvar o Buffer se o Gesto foi Detectado
        if GESTO_X_DETECTADO:
            save_buffer_to_video(frame_buffer, OUTPUT_FILENAME, FPS, frame_size)
            
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
        
    finally:
        # 7. Limpeza final
        cap.release()
        cv2.destroyAllWindows()
        hands.close()
        print("Recursos liberados.")


if __name__ == "__main__":
    run_capture_loop()