import cv2
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from PIL import Image, ImageTk
import os
import math
from datetime import datetime

ESPESSURA_GRADE_AZUL = 1  # mínimo efetivo no OpenCV
FATOR_LUPA = 3
RAIO_CAPTURA_LUPA = 20   # em pixels, antes da ampliação
MARGEM_LUPA = 10



class LaboratorioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Laboratório de Cinemática - Análise de Trajetória")
        self.root.geometry("1000x800")
        self.root.configure(bg="#f0f0f0")

        self.caminho_video = None
        self.cap = None
        self.total_frames = 0
        self.frame_atual = 0
        self.pico_frame = -1

        # FPS do vídeo (para cronômetro)
        self.fps_video = 0.0

        # Calibração temporal manual
        self.frame_t0_ref = None
        self.frame_tf_ref = None
        self.tempo_t0_ref = None
        self.tempo_tf_ref = None
        self.dt_por_frame = None


        # Pontos da calibração da escala (2 pontos com distância conhecida)
        self.pontos_escala = []

        # Pontos do sistema cartesiano:
        # [0] = origem
        # [1] = ponto qualquer com x>0 e y>0 no sistema desejado
        self.pontos_sistema = []

        # Parâmetros do sistema cartesiano/escala
        self.pixels_por_unidade = None
        self.origem_sistema = None
        self.sinal_x = 1
        self.sinal_y = 1

        # Frames processados para visualização interna
        # lista de tuplas: (numero_frame_original, frame_base_sem_marcacao)
        self.frames_processados = []
        self.indice_frame_processado = 0

        # Marcações feitas pelo usuário no modo VISUALIZANDO
        # chave = numero_frame_original
        # valor = (x_pixel, y_pixel)
        self.marcacoes_frames = {}

        # Pasta de resultados atual
        self.pasta_resultados = None
        self.frame_inicial_exportado = 0

        self.escala_tela = 1.0
        self.estado_atual = "INICIO"
        self.redimensionamento_pendente = None
        self.mouse_pos_frame = None

        self.criar_interface()

    def criar_interface(self):
        self.painel_topo = tk.Frame(self.root, bg="#e0e0e0", pady=10)
        self.painel_topo.pack(fill=tk.X)

        self.btn_carregar = tk.Button(
            self.painel_topo,
            text="1. Selecionar Vídeo",
            font=("Arial", 10, "bold"),
            command=self.carregar_video
        )
        self.btn_carregar.pack(side=tk.LEFT, padx=10)

        self.lbl_config = tk.Label(
            self.painel_topo,
            text="Frames (antes/depois):",
            font=("Arial", 10),
            bg="#e0e0e0"
        )
        self.lbl_config.pack(side=tk.LEFT, padx=(10, 2))

        self.ent_frames = tk.Entry(
            self.painel_topo,
            width=5,
            font=("Arial", 10),
            justify='center'
        )
        self.ent_frames.insert(0, "20")
        self.ent_frames.pack(side=tk.LEFT, padx=5)

        self.btn_exportar = tk.Button(
            self.painel_topo,
            text="Exportar resultados",
            font=("Arial", 10),
            command=self.exportar_resultados,
            state=tk.DISABLED
        )
        self.btn_exportar.pack(side=tk.LEFT, padx=10)

        self.lbl_instrucao = tk.Label(
            self.painel_topo,
            text="Selecione um vídeo para começar.",
            font=("Arial", 11),
            bg="#e0e0e0",
            fg="#333"
        )
        self.lbl_instrucao.pack(side=tk.LEFT, padx=20)

        self.btn_sobre = tk.Button(
            self.painel_topo,
            text="Sobre",
            font=("Arial", 9),
            command=self.mostrar_sobre
        )
        self.btn_sobre.pack(side=tk.RIGHT, padx=20)

        self.lbl_video = tk.Label(self.root, bg="black")
        self.lbl_video.pack(pady=10, expand=True, fill=tk.BOTH)

        self.lbl_status = tk.Label(
            self.root,
            text="Mouse: --",
            anchor="w",
            font=("Arial", 10),
            bg="#d9d9d9",
            fg="#222",
            padx=10,
            pady=6
        )
        self.lbl_status.pack(side=tk.BOTTOM, fill=tk.X)

        self.root.bind("<Left>", self.voltar_frame)
        self.root.bind("<Right>", self.avancar_frame)
        self.root.bind("<Return>", self.confirmar_acao)
        self.lbl_video.bind("<Button-1>", self.clique_mouse)
        self.lbl_video.bind("<Configure>", self.ao_redimensionar_janela)
        self.lbl_video.bind("<Motion>", self.atualizar_posicao_mouse)
        self.lbl_video.bind("<Leave>", self.limpar_posicao_mouse)

    def mostrar_sobre(self):
        texto = (
            "Cinemática Lab\n"
            "Análise de Trajetória e Processamento de Frames\n\n"
            "Desenvolvido por: Flávio E. S. da Cunha\n"
            "Data: 01/04/2026\n"
            "Contato: flavioescunha@gmail.com"
        )
        messagebox.showinfo("Sobre o Desenvolvedor", texto)

    def carregar_video(self):
        self.caminho_video = filedialog.askopenfilename(
            title="Selecione o vídeo",
            filetypes=[("Vídeos", "*.mp4 *.avi *.mov")]
        )
        if not self.caminho_video:
            return

        if self.cap is not None:
            self.cap.release()

        self.cap = cv2.VideoCapture(self.caminho_video)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        self.fps_video = float(self.cap.get(cv2.CAP_PROP_FPS))
        if self.fps_video <= 0:
            self.fps_video = 30.0  # fallback

        self.frame_atual = 0
        self.pico_frame = -1

        self.frame_t0_ref = None
        self.frame_tf_ref = None
        self.tempo_t0_ref = None
        self.tempo_tf_ref = None
        self.dt_por_frame = None

        self.estado_atual = "BUSCANDO_PICO"

        self.pontos_escala = []
        self.pontos_sistema = []

        self.pixels_por_unidade = None
        self.origem_sistema = None
        self.sinal_x = 1
        self.sinal_y = 1

        self.frames_processados = []
        self.indice_frame_processado = 0
        self.marcacoes_frames = {}

        self.pasta_resultados = None
        self.frame_inicial_exportado = 0

        self.btn_exportar.config(state=tk.DISABLED)
        self.lbl_status.config(text="Mouse: --")
        self.mouse_pos_frame = None

        self.lbl_instrucao.config(
            text="Use SETAS para achar o pico. ENTER para confirmar.",
            fg="blue"
        )
        self.mostrar_frame()

    def ao_redimensionar_janela(self, event):
        if self.estado_atual == "INICIO" or self.cap is None:
            return
        if self.redimensionamento_pendente is not None:
            self.root.after_cancel(self.redimensionamento_pendente)
        self.redimensionamento_pendente = self.root.after(150, self.mostrar_frame)

    def mostrar_frame(self):
        if self.estado_atual == "VISUALIZANDO":
            if not self.frames_processados:
                return

            numero_original, frame_base = self.frames_processados[self.indice_frame_processado]
            frame = self.obter_frame_com_marcacao(numero_original, frame_base)

            if self.mouse_pos_frame is not None:
                self.desenhar_lupa(frame)

            titulo = (
                f"RESULTADOS | Frame Vídeo: {numero_original} | "
                f"Progresso: {self.indice_frame_processado + 1}/{len(self.frames_processados)}"
            )
        else:
            if self.cap is None:
                return

            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_atual)
            ret, frame = self.cap.read()
            if not ret:
                return

            self.desenhar_pontos_configuracao(frame)

            if self.estado_atual == "CALIBRANDO_ESCALA" and self.mouse_pos_frame is not None:
                self.desenhar_lupa(frame)

            titulo = f"Frame: {self.frame_atual} / {self.total_frames}"


        cv2_im = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_im = Image.fromarray(cv2_im)

        largura_max = self.lbl_video.winfo_width()
        altura_max = self.lbl_video.winfo_height()

        if largura_max < 10 or altura_max < 10:
            largura_max, altura_max = 800, 500

        largura_orig, altura_orig = pil_im.size
        self.escala_tela = min(largura_max / largura_orig, altura_max / altura_orig)

        nova_largura = int(largura_orig * self.escala_tela)
        nova_altura = int(altura_orig * self.escala_tela)

        pil_im = pil_im.resize((nova_largura, nova_altura), Image.Resampling.LANCZOS)
        self.foto = ImageTk.PhotoImage(image=pil_im)
        self.lbl_video.config(image=self.foto)
        self.root.title(titulo)

    def desenhar_pontos_configuracao(self, frame):
        # Pontos da escala: vermelho
        for i, pt in enumerate(self.pontos_escala):
            cv2.circle(frame, pt, 5, (0, 0, 255), -1)
            cv2.putText(
                frame, f"E{i+1}", (pt[0] + 8, pt[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA
            )

        # Pontos do sistema cartesiano
        if len(self.pontos_sistema) >= 1:
            origem = self.pontos_sistema[0]
            cv2.circle(frame, origem, 6, (0, 255, 255), -1)
            cv2.putText(
                frame, "O", (origem[0] + 8, origem[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA
            )

        if len(self.pontos_sistema) >= 2:
            q1 = self.pontos_sistema[1]
            cv2.circle(frame, q1, 6, (0, 255, 0), -1)
            cv2.putText(
                frame, "Q+", (q1[0] + 8, q1[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA
            )

    def avancar_frame(self, event):
        if self.estado_atual in ["BUSCANDO_PICO", "ESCOLHENDO_T0", "ESCOLHENDO_TF"] and self.frame_atual < self.total_frames - 1:
            self.frame_atual += 1
            self.mostrar_frame()
        elif self.estado_atual == "VISUALIZANDO" and self.indice_frame_processado < len(self.frames_processados) - 1:
            self.indice_frame_processado += 1
            self.mostrar_frame()

    def voltar_frame(self, event):
        if self.estado_atual in ["BUSCANDO_PICO", "ESCOLHENDO_T0", "ESCOLHENDO_TF"] and self.frame_atual > 0:
            self.frame_atual -= 1
            self.mostrar_frame()
        elif self.estado_atual == "VISUALIZANDO" and self.indice_frame_processado > 0:
            self.indice_frame_processado -= 1
            self.mostrar_frame()


    def confirmar_acao(self, event):
        if self.estado_atual == "BUSCANDO_PICO":
            self.pico_frame = self.frame_atual
            self.estado_atual = "CALIBRANDO_ESCALA"
            self.pontos_escala = []
            self.lbl_instrucao.config(
                text="Pico salvo! Clique em 2 pontos com distância conhecida e aperte ENTER.",
                fg="red"
            )
            self.mostrar_frame()

        elif self.estado_atual == "CALIBRANDO_ESCALA":
            if len(self.pontos_escala) == 2:
                self.estado_atual = "DEFININDO_SISTEMA"
                self.pontos_sistema = []
                self.lbl_instrucao.config(
                    text="Agora clique na ORIGEM e depois em um ponto com x>0 e y>0. Aperte ENTER.",
                    fg="#AA5500"
                )
                self.mostrar_frame()
            else:
                messagebox.showwarning("Atenção", "Clique primeiro em 2 pontos para definir a escala.")

        elif self.estado_atual == "DEFININDO_SISTEMA":
            if len(self.pontos_sistema) == 2:
                self.estado_atual = "ESCOLHENDO_T0"
                self.lbl_instrucao.config(
                    text="Agora use as SETAS para escolher o frame de t0 e aperte ENTER.",
                    fg="#006699"
                )
                self.mostrar_frame()
            else:
                messagebox.showwarning(
                    "Atenção",
                    "Clique na origem e depois em um ponto do primeiro quadrante."
                )

        elif self.estado_atual == "ESCOLHENDO_T0":
            self.frame_t0_ref = self.frame_atual
            tempo_t0 = simpledialog.askfloat(
                "Calibração temporal",
                "Digite o tempo real mostrado neste frame t0 (em segundos):"
            )

            if tempo_t0 is None:
                return

            self.tempo_t0_ref = tempo_t0
            self.estado_atual = "ESCOLHENDO_TF"
            self.lbl_instrucao.config(
                text="Agora use as SETAS para escolher o frame de tf e aperte ENTER.",
                fg="#006699"
            )
            self.mostrar_frame()

        elif self.estado_atual == "ESCOLHENDO_TF":
            self.frame_tf_ref = self.frame_atual
            tempo_tf = simpledialog.askfloat(
                "Calibração temporal",
                "Digite o tempo real mostrado neste frame tf (em segundos):"
            )

            if tempo_tf is None:
                return

            self.tempo_tf_ref = tempo_tf
            self.processar_analise()


    def clique_mouse(self, event):
        if not hasattr(self, "foto"):
            return

        largura_imagem = self.foto.width()
        altura_imagem = self.foto.height()
        espaco_x = (self.lbl_video.winfo_width() - largura_imagem) // 2
        espaco_y = (self.lbl_video.winfo_height() - altura_imagem) // 2

        clique_x = event.x - espaco_x
        clique_y = event.y - espaco_y

        if not (0 <= clique_x <= largura_imagem and 0 <= clique_y <= altura_imagem):
            return

        x_real = int(clique_x / self.escala_tela)
        y_real = int(clique_y / self.escala_tela)
        ponto = (x_real, y_real)

        if self.estado_atual == "CALIBRANDO_ESCALA":
            if len(self.pontos_escala) < 2:
                self.pontos_escala.append(ponto)
                self.mostrar_frame()

        elif self.estado_atual == "DEFININDO_SISTEMA":
            if len(self.pontos_sistema) < 2:
                self.pontos_sistema.append(ponto)
                self.mostrar_frame()

        elif self.estado_atual == "VISUALIZANDO":
            self.registrar_marcacao_frame_atual(x_real, y_real)
            self.mostrar_frame()

    def limpar_posicao_mouse(self, event=None):
        self.lbl_status.config(text="Mouse: --")
        self.mouse_pos_frame = None

        if self.estado_atual in ["CALIBRANDO_ESCALA", "VISUALIZANDO"]:
            self.mostrar_frame()


    def pixel_para_coordenadas(self, x_pixel, y_pixel):
        if self.origem_sistema is None or self.pixels_por_unidade is None or self.pixels_por_unidade <= 0:
            return None

        x0, y0 = self.origem_sistema

        x_coord = ((x_pixel - x0) / self.pixels_por_unidade) * self.sinal_x
        y_coord = ((y_pixel - y0) / self.pixels_por_unidade) * self.sinal_y

        return x_coord, y_coord

    def atualizar_posicao_mouse(self, event):
        if not hasattr(self, "foto"):
            self.lbl_status.config(text="Mouse: --")
            self.mouse_pos_frame = None
            return

        largura_imagem = self.foto.width()
        altura_imagem = self.foto.height()

        espaco_x = (self.lbl_video.winfo_width() - largura_imagem) // 2
        espaco_y = (self.lbl_video.winfo_height() - altura_imagem) // 2

        clique_x = event.x - espaco_x
        clique_y = event.y - espaco_y

        if not (0 <= clique_x <= largura_imagem and 0 <= clique_y <= altura_imagem):
            self.lbl_status.config(text="Mouse: fora da imagem")
            if self.mouse_pos_frame is not None:
                self.mouse_pos_frame = None
                if self.estado_atual in ["CALIBRANDO_ESCALA", "VISUALIZANDO"]:
                    self.mostrar_frame()
            return

        x_real = int(clique_x / self.escala_tela)
        y_real = int(clique_y / self.escala_tela)

        self.mouse_pos_frame = (x_real, y_real)

        coords = self.pixel_para_coordenadas(x_real, y_real)

        if coords is None:
            self.lbl_status.config(text=f"Mouse (pixel): x = {x_real}, y = {y_real}")
        else:
            x_coord, y_coord = coords
            self.lbl_status.config(
                text=f"Mouse: x = {x_coord:.2f} | y = {y_coord:.2f}"
            )

        if self.estado_atual in ["CALIBRANDO_ESCALA", "VISUALIZANDO"]:
            self.mostrar_frame()

    def escrever_texto_contornado(self, frame, texto, pos, escala=0.45,
                                  cor_texto=(0, 0, 0), cor_contorno=(255, 255, 255),
                                  espessura_texto=1, espessura_contorno=3):
        x, y = pos
        cv2.putText(
            frame, texto, (x, y),
            cv2.FONT_HERSHEY_SIMPLEX, escala, cor_contorno,
            espessura_contorno, cv2.LINE_AA
        )
        cv2.putText(
            frame, texto, (x, y),
            cv2.FONT_HERSHEY_SIMPLEX, escala, cor_texto,
            espessura_texto, cv2.LINE_AA
        )

    def desenhar_lupa(self, frame):
        if self.mouse_pos_frame is None:
            return

        x_mouse, y_mouse = self.mouse_pos_frame
        alt, larg, _ = frame.shape

        raio = RAIO_CAPTURA_LUPA
        fator = FATOR_LUPA
        margem = MARGEM_LUPA

        x1 = max(0, x_mouse - raio)
        y1 = max(0, y_mouse - raio)
        x2 = min(larg, x_mouse + raio + 1)
        y2 = min(alt, y_mouse + raio + 1)

        recorte = frame[y1:y2, x1:x2].copy()
        if recorte.size == 0:
            return

        lupa = cv2.resize(
            recorte,
            (recorte.shape[1] * fator, recorte.shape[0] * fator),
            interpolation=cv2.INTER_NEAREST
        )

        # Desenha cruz no ponto correspondente ao mouse dentro da lupa
        cx = (x_mouse - x1) * fator
        cy = (y_mouse - y1) * fator

        cv2.line(lupa, (cx, 0), (cx, lupa.shape[0] - 1), (255, 255, 255), 1)
        cv2.line(lupa, (0, cy), (lupa.shape[1] - 1, cy), (255, 255, 255), 1)
        cv2.line(lupa, (cx, 0), (cx, lupa.shape[0] - 1), (0, 0, 0), 1)
        cv2.line(lupa, (0, cy), (lupa.shape[1] - 1, cy), (0, 0, 0), 1)

        h_lupa, w_lupa = lupa.shape[:2]

        # Se a lupa ficar grande demais para o frame, reduz proporcionalmente
        max_w = larg - 2 * margem
        max_h = alt - 2 * margem
        if w_lupa > max_w or h_lupa > max_h:
            escala = min(max_w / w_lupa, max_h / h_lupa)
            novo_w = max(20, int(w_lupa * escala))
            novo_h = max(20, int(h_lupa * escala))
            lupa = cv2.resize(lupa, (novo_w, novo_h), interpolation=cv2.INTER_NEAREST)
            h_lupa, w_lupa = lupa.shape[:2]

        x_dest = margem
        y_dest = margem

        frame[y_dest:y_dest + h_lupa, x_dest:x_dest + w_lupa] = lupa

        # Borda da lupa
        cv2.rectangle(
            frame,
            (x_dest, y_dest),
            (x_dest + w_lupa - 1, y_dest + h_lupa - 1),
            (255, 255, 255),
            2
        )
        cv2.rectangle(
            frame,
            (x_dest, y_dest),
            (x_dest + w_lupa - 1, y_dest + h_lupa - 1),
            (0, 0, 0),
            1
        )

        # Texto "3x"
        self.escrever_texto_contornado(
            frame,
            f"{FATOR_LUPA}x",
            (x_dest + 6, y_dest + 18),
            escala=0.6,
            cor_texto=(255, 255, 255),
            cor_contorno=(0, 0, 0),
            espessura_texto=2,
            espessura_contorno=4
        )
    
    def desenhar_cronometro(self, frame, tempo_seg):
        alt, larg, _ = frame.shape
        texto = f"{tempo_seg:.2f} s".replace(".", ",")

        x = 15
        y = alt - 15

        self.escrever_texto_contornado(
            frame,
            texto,
            (x, y),
            escala=0.8,
            cor_texto=(255, 255, 255),
            cor_contorno=(0, 0, 0),
            espessura_texto=2,
            espessura_contorno=4
        )

    def desenhar_grade_cartesiana(self, frame, origem, sinal_x, sinal_y, pixels_por_unidade):
        alt, larg, _ = frame.shape

        azul = (255, 0, 0)
        preto = (0, 0, 0)

        espessura_grade = ESPESSURA_GRADE_AZUL
        espessura_eixos = 2
        tamanho_traco = 6

        x0, y0 = origem

        # Linhas verticais (grade em x) - sentido positivo
        k = 1
        while True:
            x = x0 + k * sinal_x * pixels_por_unidade
            if not (0 <= x < larg):
                break
            x_int = int(round(x))
            cv2.line(frame, (x_int, 0), (x_int, alt), azul, espessura_grade)

            if k % 5 == 0:
                if 0 <= y0 < alt:
                    cv2.line(
                        frame,
                        (x_int, y0 - tamanho_traco),
                        (x_int, y0 + tamanho_traco),
                        preto,
                        2
                    )

                y_texto = y0 - 8 if y0 > 20 else y0 + 18
                self.escrever_texto_contornado(
                    frame, str(k), (x_int + 2, int(y_texto)),
                    escala=0.45, cor_texto=preto
                )
            k += 1

        # Linhas verticais (grade em x) - sentido negativo
        k = 1
        while True:
            x = x0 - k * sinal_x * pixels_por_unidade
            if not (0 <= x < larg):
                break
            x_int = int(round(x))
            cv2.line(frame, (x_int, 0), (x_int, alt), azul, espessura_grade)

            if k % 5 == 0:
                if 0 <= y0 < alt:
                    cv2.line(
                        frame,
                        (x_int, y0 - tamanho_traco),
                        (x_int, y0 + tamanho_traco),
                        preto,
                        2
                    )

                y_texto = y0 - 8 if y0 > 20 else y0 + 18
                self.escrever_texto_contornado(
                    frame, str(-k), (x_int + 2, int(y_texto)),
                    escala=0.45, cor_texto=preto
                )
            k += 1

        # Linhas horizontais (grade em y) - sentido positivo
        k = 1
        while True:
            y = y0 + k * sinal_y * pixels_por_unidade
            if not (0 <= y < alt):
                break
            y_int = int(round(y))
            cv2.line(frame, (0, y_int), (larg, y_int), azul, espessura_grade)

            if k % 5 == 0:
                if 0 <= x0 < larg:
                    cv2.line(
                        frame,
                        (x0 - tamanho_traco, y_int),
                        (x0 + tamanho_traco, y_int),
                        preto,
                        2
                    )

                x_texto = x0 + 6 if x0 < larg - 50 else x0 - 35
                self.escrever_texto_contornado(
                    frame, str(k), (int(x_texto), y_int - 3),
                    escala=0.45, cor_texto=preto
                )
            k += 1

        # Linhas horizontais (grade em y) - sentido negativo
        k = 1
        while True:
            y = y0 - k * sinal_y * pixels_por_unidade
            if not (0 <= y < alt):
                break
            y_int = int(round(y))
            cv2.line(frame, (0, y_int), (larg, y_int), azul, espessura_grade)

            if k % 5 == 0:
                if 0 <= x0 < larg:
                    cv2.line(
                        frame,
                        (x0 - tamanho_traco, y_int),
                        (x0 + tamanho_traco, y_int),
                        preto,
                        2
                    )

                x_texto = x0 + 6 if x0 < larg - 50 else x0 - 35
                self.escrever_texto_contornado(
                    frame, str(-k), (int(x_texto), y_int - 3),
                    escala=0.45, cor_texto=preto
                )
            k += 1

        # Eixos cartesianos
        if 0 <= x0 < larg:
            cv2.line(frame, (x0, 0), (x0, alt), preto, espessura_eixos)

        if 0 <= y0 < alt:
            cv2.line(frame, (0, y0), (larg, y0), preto, espessura_eixos)

        # Origem
        cv2.circle(frame, (x0, y0), 5, preto, -1)
        self.escrever_texto_contornado(
            frame, "0", (x0 + 6, y0 - 6),
            escala=0.5, cor_texto=preto
        )

    def registrar_marcacao_frame_atual(self, x_pixel, y_pixel):
        if self.estado_atual != "VISUALIZANDO":
            return
        if not self.frames_processados:
            return

        numero_original, _ = self.frames_processados[self.indice_frame_processado]
        self.marcacoes_frames[numero_original] = (x_pixel, y_pixel)

    def obter_tempo_do_frame(self, numero_frame_original):
        if (
            self.dt_por_frame is not None and
            self.frame_t0_ref is not None and
            self.tempo_t0_ref is not None
        ):
            return self.tempo_t0_ref + (numero_frame_original - self.frame_t0_ref) * self.dt_por_frame

        return (numero_frame_original - self.frame_inicial_exportado) / self.fps_video


    def desenhar_marcacao_ponto(self, frame, numero_frame_original, x_pixel, y_pixel):
        coords = self.pixel_para_coordenadas(x_pixel, y_pixel)
        if coords is None:
            return

        x_coord, y_coord = coords
        tempo_seg = self.obter_tempo_do_frame(numero_frame_original)

        # bolinha branca
        cv2.circle(frame, (x_pixel, y_pixel), 6, (255, 255, 255), -1)
        cv2.circle(frame, (x_pixel, y_pixel), 8, (0, 0, 0), 1)

        texto = f"({tempo_seg:.3f}, {x_coord:.2f}, {y_coord:.2f})".replace(".", ",")

        alt, larg, _ = frame.shape

        # Preferência: abaixo do ponto
        x_texto = x_pixel + 8
        y_texto = y_pixel + 22

        # Evita sair pela direita
        if x_texto > larg - 220:
            x_texto = max(10, x_pixel - 200)

        # Se ficar muito perto da borda inferior, sobe o texto
        if y_texto > alt - 10:
            y_texto = max(20, y_pixel - 12)

        self.escrever_texto_contornado(
            frame,
            texto,
            (x_texto, y_texto),
            escala=0.55,
            cor_texto=(255, 255, 255),
            cor_contorno=(0, 0, 0),
            espessura_texto=2,
            espessura_contorno=4
        )

    def obter_frame_com_marcacao(self, numero_frame_original, frame_base):
        frame = frame_base.copy()

        if numero_frame_original in self.marcacoes_frames:
            x_pixel, y_pixel = self.marcacoes_frames[numero_frame_original]
            self.desenhar_marcacao_ponto(frame, numero_frame_original, x_pixel, y_pixel)

        return frame

    def exportar_resultados(self):
        if not self.frames_processados or not self.pasta_resultados:
            messagebox.showwarning("Atenção", "Ainda não há resultados processados para exportar.")
            return

        try:
            for numero_original, frame_base in self.frames_processados:
                frame_final = self.obter_frame_com_marcacao(numero_original, frame_base)
                caminho_saida = os.path.join(self.pasta_resultados, f"Frame_{numero_original:04d}.jpg")
                cv2.imwrite(caminho_saida, frame_final)

            messagebox.showinfo(
                "Exportação concluída",
                f"Os frames foram exportados/atualizados em:\n\n{self.pasta_resultados}"
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar os resultados:\n\n{e}")

    def processar_analise(self):
        try:
            num_offset = int(self.ent_frames.get())
            if num_offset < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erro", "Digite um número inteiro válido para os frames.")
            return

        if len(self.pontos_escala) != 2:
            messagebox.showerror("Erro", "A escala precisa de 2 pontos.")
            return

        if self.frame_t0_ref is None or self.frame_tf_ref is None:
            messagebox.showerror("Erro", "Defina os frames de t0 e tf.")
            return

        if self.tempo_t0_ref is None or self.tempo_tf_ref is None:
            messagebox.showerror("Erro", "Defina os tempos reais de t0 e tf.")
            return

        delta_frames = self.frame_tf_ref - self.frame_t0_ref
        if delta_frames == 0:
            messagebox.showerror("Erro", "Os frames de t0 e tf não podem ser o mesmo.")
            return

        dt_por_frame = (self.tempo_tf_ref - self.tempo_t0_ref) / delta_frames
        if dt_por_frame <= 0:
            messagebox.showerror(
                "Erro",
                "A calibração temporal ficou inválida.\n\nVerifique se tf > t0 e se o frame de tf vem depois do frame de t0."
            )
            return

        self.dt_por_frame = dt_por_frame

        # Escala por Pitágoras
        (x1, y1), (x2, y2) = self.pontos_escala
        distancia_pixels = math.hypot(x2 - x1, y2 - y1)

        if distancia_pixels == 0:
            messagebox.showerror("Erro", "Os dois pontos da escala não podem coincidir.")
            return

        distancia_real = simpledialog.askfloat(
            "Calibração",
            "Distância real entre os 2 pontos (em cm):"
        )

        if not distancia_real or distancia_real <= 0:
            messagebox.showwarning("Atenção", "A distância real precisa ser positiva.")
            return

        pixels_por_unidade = distancia_pixels / distancia_real

        if pixels_por_unidade <= 0:
            messagebox.showerror("Erro", "Não foi possível calcular a escala.")
            return

        # Sistema cartesiano
        origem = self.pontos_sistema[0]
        ponto_q1 = self.pontos_sistema[1]

        if ponto_q1[0] == origem[0] or ponto_q1[1] == origem[1]:
            messagebox.showerror(
                "Erro",
                "O ponto do primeiro quadrante não pode estar alinhado horizontalmente ou verticalmente com a origem."
            )
            return

        sinal_x = 1 if ponto_q1[0] > origem[0] else -1
        sinal_y = 1 if ponto_q1[1] > origem[1] else -1

        # Salva parâmetros para uso no mouse / visualização
        self.pixels_por_unidade = pixels_por_unidade
        self.origem_sistema = origem
        self.sinal_x = sinal_x
        self.sinal_y = sinal_y

        agora = datetime.now()
        timestamp = agora.strftime("%Y-%m-%d %H-%M")
        nome_pasta = f"Experimento de {timestamp}"

        os.makedirs(nome_pasta, exist_ok=True)
        self.pasta_resultados = nome_pasta

        inicio = max(0, self.pico_frame - num_offset)
        fim = min(self.total_frames, self.pico_frame + num_offset + 1)
        self.frame_inicial_exportado = inicio

        self.lbl_instrucao.config(text=f"Processando {fim - inicio} frames...", fg="green")
        self.root.update()

        self.frames_processados = []
        self.indice_frame_processado = 0
        self.marcacoes_frames = {}

        for f in range(inicio, fim):
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ret, frame = self.cap.read()
            if not ret:
                continue

            self.desenhar_grade_cartesiana(
                frame=frame,
                origem=origem,
                sinal_x=sinal_x,
                sinal_y=sinal_y,
                pixels_por_unidade=pixels_por_unidade
            )

            tempo_seg = self.obter_tempo_do_frame(f)
            self.desenhar_cronometro(frame, tempo_seg)


            # salva frame-base sem marcação de ponto
            self.frames_processados.append((f, frame.copy()))

        # exporta a primeira versão automaticamente
        self.exportar_resultados()

        self.estado_atual = "VISUALIZANDO"
        self.btn_exportar.config(state=tk.NORMAL)
        self.lbl_instrucao.config(
            text="Use as SETAS para navegar. Clique no frame para marcar um ponto. O tempo agora usa a calibração manual t0/tf.",
            fg="#800080"
        )
        self.mostrar_frame()

        messagebox.showinfo(
            "Sucesso!",
            f"Processo concluído!\n\n"
            f"Agora você pode navegar pelas imagens, clicar para marcar um ponto em cada frame e exportar novamente.\n\n"
            f"Pasta de saída: '{nome_pasta}'"
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = LaboratorioApp(root)
    root.mainloop()