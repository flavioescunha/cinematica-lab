import cv2
import tkinter as tk
from tkinter import filedialog, messagebox
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
        self.root.geometry("1200x800")
        self.root.configure(bg="#f0f0f0")

        self.caminho_video = None
        self.cap = None
        self.total_frames = 0
        self.frame_atual = 0
        self.pico_frame = -1

        self.fps_video = 0.0

        # Paralaxe
        self.var_D = tk.StringVar(value="")
        self.var_d = tk.StringVar(value="")
        self.fator_paralaxe = 1.0

        # Calibração temporal manual
        self.frame_t0_ref = None
        self.frame_tf_ref = None
        self.tempo_t0_ref = None
        self.tempo_tf_ref = None
        self.dt_por_frame = None

        # Pontos da calibração da escala
        self.pontos_escala = [None, None]

        # Pontos do sistema cartesiano
        self.pontos_sistema = [None, None]

        # Parâmetros do sistema cartesiano/escala
        self.pixels_por_unidade = None
        self.origem_sistema = None
        self.sinal_x = 1
        self.sinal_y = 1

        # Frames processados
        self.frames_processados = []
        self.indice_frame_processado = 0

        # Marcações feitas no modo VISUALIZANDO
        self.marcacoes_frames = {}

        # Pasta de resultados
        self.pasta_resultados = None
        self.frame_inicial_exportado = 0

        self.escala_tela = 1.0
        self.estado_atual = "INICIO"
        self.redimensionamento_pendente = None
        self.mouse_pos_frame = None

        # Modo de captura de ponto no painel
        self.modo_captura_config = None

        # Widgets bloqueáveis após processamento
        self.widgets_configuracao = []

        self.criar_interface()

    # ============================================================
    # INTERFACE
    # ============================================================

    def criar_interface(self):
        self.container_principal = tk.Frame(self.root, bg="#f0f0f0")
        self.container_principal.pack(fill=tk.BOTH, expand=True)

        self.painel_esquerdo = tk.Frame(
            self.container_principal,
            bg="#e6e6e6",
            width=300,
            padx=10,
            pady=10
        )
        self.painel_esquerdo.pack(side=tk.LEFT, fill=tk.Y)
        self.painel_esquerdo.pack_propagate(False)

        self.area_direita = tk.Frame(self.container_principal, bg="#f0f0f0")
        self.area_direita.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.criar_painel_controle()

        self.lbl_video = tk.Label(self.area_direita, bg="black")
        self.lbl_video.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)

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

        self.bloquear_painel_configuracao()

    def criar_painel_controle(self):
        titulo = tk.Label(
            self.painel_esquerdo,
            text="Painel de controle",
            font=("Arial", 13, "bold"),
            bg="#e6e6e6"
        )
        titulo.pack(anchor="w", pady=(0, 10))

        self.btn_carregar = tk.Button(
            self.painel_esquerdo,
            text="Selecionar vídeo",
            font=("Arial", 10, "bold"),
            command=self.carregar_video
        )
        self.btn_carregar.pack(fill=tk.X, pady=3)

        self.btn_exportar = tk.Button(
            self.painel_esquerdo,
            text="Exportar resultados",
            font=("Arial", 10),
            command=self.exportar_resultados,
            state=tk.DISABLED
        )
        self.btn_exportar.pack(fill=tk.X, pady=3)

        self.btn_sobre = tk.Button(
            self.painel_esquerdo,
            text="Sobre",
            font=("Arial", 9),
            command=self.mostrar_sobre
        )
        self.btn_sobre.pack(fill=tk.X, pady=(3, 10))

        self.lbl_instrucao = tk.Label(
            self.painel_esquerdo,
            text="Selecione um vídeo para começar.",
            font=("Arial", 10),
            bg="#e6e6e6",
            fg="#333",
            wraplength=270,
            justify="left"
        )
        self.lbl_instrucao.pack(anchor="w", pady=(0, 10))

        self.var_frame_atual = tk.StringVar(value="Frame atual: --")
        self.lbl_frame_atual = tk.Label(
            self.painel_esquerdo,
            textvariable=self.var_frame_atual,
            font=("Arial", 10, "bold"),
            bg="#e6e6e6"
        )
        self.lbl_frame_atual.pack(anchor="w")

        self.scale_frames = tk.Scale(
            self.painel_esquerdo,
            from_=0,
            to=0,
            orient=tk.HORIZONTAL,
            showvalue=True,
            command=self.atualizar_frame_por_slider,
            length=260
        )
        self.scale_frames.pack(fill=tk.X, pady=(0, 10))
        self.widgets_configuracao.append(self.scale_frames)

        self.var_frames_offset = tk.StringVar(value="20")
        self.var_distancia_real = tk.StringVar(value="")
        self.var_pico_frame = tk.StringVar(value="")
        self.var_t0_frame = tk.StringVar(value="")
        self.var_t0_tempo = tk.StringVar(value="")
        self.var_tf_frame = tk.StringVar(value="")
        self.var_tf_tempo = tk.StringVar(value="")

        self.var_ponto_escala_1 = tk.StringVar(value="não definido")
        self.var_ponto_escala_2 = tk.StringVar(value="não definido")
        self.var_origem = tk.StringVar(value="não definido")
        self.var_quadrante = tk.StringVar(value="não definido")

        self.criar_separador("Extração")
        self.criar_linha_frame_central()
        self.criar_linha_entry("Frames antes/depois:", self.var_frames_offset)

        self.criar_separador("Escala espacial")
        self.criar_linha_ponto("Ponto escala 1:", self.var_ponto_escala_1, "ESCALA_1")
        self.criar_linha_ponto("Ponto escala 2:", self.var_ponto_escala_2, "ESCALA_2")
        self.criar_linha_entry("Distância conhecida (cm):", self.var_distancia_real)

        self.criar_separador("Correção de paralaxe")
        self.criar_linha_entry("Distância câmera D (cm):", self.var_D)
        self.criar_linha_entry("Distância objeto d (cm):", self.var_d)

        self.criar_separador("Sistema cartesiano")
        self.criar_linha_ponto("Origem:", self.var_origem, "ORIGEM")
        self.criar_linha_ponto("Quadrante +:", self.var_quadrante, "QUADRANTE")

        self.criar_separador("Tempo")
        self.criar_linha_frame_tempo("t0", self.var_t0_frame, self.var_t0_tempo, "T0")
        self.criar_linha_frame_tempo("tf", self.var_tf_frame, self.var_tf_tempo, "TF")

        self.criar_separador("Processamento")
        self.btn_processar = tk.Button(
            self.painel_esquerdo,
            text="Processar frames",
            font=("Arial", 11, "bold"),
            bg="#cdeccd",
            command=self.processar_analise
        )
        self.btn_processar.pack(fill=tk.X, pady=(8, 3))
        self.widgets_configuracao.append(self.btn_processar)

    def criar_separador(self, texto):
        lbl = tk.Label(
            self.painel_esquerdo,
            text=texto,
            font=("Arial", 10, "bold"),
            bg="#d0d0d0",
            anchor="w",
            padx=5
        )
        lbl.pack(fill=tk.X, pady=(8, 4))

    def criar_linha_entry(self, rotulo, variavel):
        frame = tk.Frame(self.painel_esquerdo, bg="#e6e6e6")
        frame.pack(fill=tk.X, pady=2)

        lbl = tk.Label(frame, text=rotulo, bg="#e6e6e6", anchor="w", width=20)
        lbl.pack(side=tk.LEFT)

        ent = tk.Entry(frame, textvariable=variavel, width=10)
        ent.pack(side=tk.RIGHT)

        self.widgets_configuracao.append(ent)

    def criar_linha_frame_central(self):
        frame = tk.Frame(self.painel_esquerdo, bg="#e6e6e6")
        frame.pack(fill=tk.X, pady=2)

        lbl = tk.Label(frame, text="Frame central:", bg="#e6e6e6", anchor="w")
        lbl.pack(side=tk.LEFT)

        ent = tk.Entry(frame, textvariable=self.var_pico_frame, width=8)
        ent.pack(side=tk.LEFT, padx=4)

        btn = tk.Button(frame, text="☝ atual", command=self.definir_frame_central)
        btn.pack(side=tk.RIGHT)

        self.widgets_configuracao.extend([ent, btn])

    def criar_linha_ponto(self, rotulo, variavel, modo):
        frame = tk.Frame(self.painel_esquerdo, bg="#e6e6e6")
        frame.pack(fill=tk.X, pady=2)

        lbl = tk.Label(frame, text=rotulo, bg="#e6e6e6", anchor="w", width=14)
        lbl.pack(side=tk.LEFT)

        lbl_valor = tk.Label(
            frame,
            textvariable=variavel,
            bg="#e6e6e6",
            anchor="w",
            width=13
        )
        lbl_valor.pack(side=tk.LEFT)

        btn = tk.Button(
            frame,
            text="☝",
            width=3,
            command=lambda m=modo: self.ativar_captura_ponto(m)
        )
        btn.pack(side=tk.RIGHT)

        self.widgets_configuracao.append(btn)

    def criar_linha_frame_tempo(self, nome, var_frame, var_tempo, tipo):
        frame = tk.Frame(self.painel_esquerdo, bg="#e6e6e6")
        frame.pack(fill=tk.X, pady=2)

        lbl = tk.Label(frame, text=f"{nome} frame:", bg="#e6e6e6", width=8, anchor="w")
        lbl.pack(side=tk.LEFT)

        ent_frame = tk.Entry(frame, textvariable=var_frame, width=6)
        ent_frame.pack(side=tk.LEFT)

        lbl_t = tk.Label(frame, text="s:", bg="#e6e6e6")
        lbl_t.pack(side=tk.LEFT, padx=(5, 1))

        ent_tempo = tk.Entry(frame, textvariable=var_tempo, width=7)
        ent_tempo.pack(side=tk.LEFT)

        btn = tk.Button(
            frame,
            text="☝ atual",
            command=lambda t=tipo: self.definir_frame_temporal(t)
        )
        btn.pack(side=tk.RIGHT)

        self.widgets_configuracao.extend([ent_frame, ent_tempo, btn])

    def bloquear_painel_configuracao(self):
        for w in self.widgets_configuracao:
            try:
                w.config(state=tk.DISABLED)
            except Exception:
                pass

    def desbloquear_painel_configuracao(self):
        for w in self.widgets_configuracao:
            try:
                w.config(state=tk.NORMAL)
            except Exception:
                pass

    def atualizar_label_frame_atual(self):
        if self.total_frames > 0:
            self.var_frame_atual.set(f"Frame atual: {self.frame_atual} / {self.total_frames - 1}")
        else:
            self.var_frame_atual.set("Frame atual: --")

    # ============================================================
    # CARREGAMENTO
    # ============================================================

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
            self.fps_video = 30.0

        self.frame_atual = 0
        self.pico_frame = -1

        self.frame_t0_ref = None
        self.frame_tf_ref = None
        self.tempo_t0_ref = None
        self.tempo_tf_ref = None
        self.dt_por_frame = None
        self.fator_paralaxe = 1.0

        self.estado_atual = "CONFIGURANDO"
        self.modo_captura_config = None

        self.pontos_escala = [None, None]
        self.pontos_sistema = [None, None]

        self.pixels_por_unidade = None
        self.origem_sistema = None
        self.sinal_x = 1
        self.sinal_y = 1

        self.frames_processados = []
        self.indice_frame_processado = 0
        self.marcacoes_frames = {}

        self.pasta_resultados = None
        self.frame_inicial_exportado = 0
        self.mouse_pos_frame = None

        self.var_pico_frame.set("")
        self.var_distancia_real.set("")
        self.var_t0_frame.set("")
        self.var_t0_tempo.set("")
        self.var_tf_frame.set("")
        self.var_tf_tempo.set("")

        self.atualizar_variaveis_pontos()
        self.atualizar_label_frame_atual()

        self.scale_frames.config(from_=0, to=max(0, self.total_frames - 1))
        self.scale_frames.set(0)

        self.desbloquear_painel_configuracao()
        self.btn_exportar.config(state=tk.DISABLED)

        self.lbl_status.config(text="Mouse: --")
        self.lbl_instrucao.config(
            text="Use o controle deslizante ou as setas. Configure os campos à esquerda e clique em Processar frames.",
            fg="blue"
        )

        self.mostrar_frame()

    # ============================================================
    # NAVEGAÇÃO
    # ============================================================

    def atualizar_frame_por_slider(self, valor):
        if self.estado_atual != "CONFIGURANDO" or self.cap is None:
            return

        try:
            self.frame_atual = int(float(valor))
        except ValueError:
            return

        self.atualizar_label_frame_atual()
        self.mostrar_frame()

    def avancar_frame(self, event=None):
        if self.estado_atual == "CONFIGURANDO" and self.frame_atual < self.total_frames - 1:
            self.frame_atual += 1
            self.scale_frames.set(self.frame_atual)
            self.atualizar_label_frame_atual()
            self.mostrar_frame()

        elif self.estado_atual == "VISUALIZANDO" and self.indice_frame_processado < len(self.frames_processados) - 1:
            self.indice_frame_processado += 1
            self.mostrar_frame()

    def voltar_frame(self, event=None):
        if self.estado_atual == "CONFIGURANDO" and self.frame_atual > 0:
            self.frame_atual -= 1
            self.scale_frames.set(self.frame_atual)
            self.atualizar_label_frame_atual()
            self.mostrar_frame()

        elif self.estado_atual == "VISUALIZANDO" and self.indice_frame_processado > 0:
            self.indice_frame_processado -= 1
            self.mostrar_frame()

    def confirmar_acao(self, event=None):
        # A nova lógica usa o painel. ENTER fica reservado para futuras funções.
        pass

    def ao_redimensionar_janela(self, event):
        if self.estado_atual == "INICIO" or self.cap is None:
            return
        if self.redimensionamento_pendente is not None:
            self.root.after_cancel(self.redimensionamento_pendente)
        self.redimensionamento_pendente = self.root.after(150, self.mostrar_frame)

    # ============================================================
    # CONFIGURAÇÃO PELO PAINEL
    # ============================================================

    def definir_frame_central(self):
        if self.estado_atual != "CONFIGURANDO":
            return

        self.pico_frame = self.frame_atual
        self.var_pico_frame.set(str(self.pico_frame))
        self.lbl_instrucao.config(
            text=f"Frame central definido: {self.pico_frame}.",
            fg="blue"
        )

    def definir_frame_temporal(self, tipo):
        if self.estado_atual != "CONFIGURANDO":
            return

        if tipo == "T0":
            self.frame_t0_ref = self.frame_atual
            self.var_t0_frame.set(str(self.frame_t0_ref))
            self.lbl_instrucao.config(
                text=f"Frame t0 definido: {self.frame_t0_ref}. Digite o tempo correspondente.",
                fg="#006699"
            )

        elif tipo == "TF":
            self.frame_tf_ref = self.frame_atual
            self.var_tf_frame.set(str(self.frame_tf_ref))
            self.lbl_instrucao.config(
                text=f"Frame tf definido: {self.frame_tf_ref}. Digite o tempo correspondente.",
                fg="#006699"
            )

    def ativar_captura_ponto(self, modo):
        if self.estado_atual != "CONFIGURANDO":
            return

        self.modo_captura_config = modo

        textos = {
            "ESCALA_1": "Clique na imagem para definir o ponto 1 da escala.",
            "ESCALA_2": "Clique na imagem para definir o ponto 2 da escala.",
            "ORIGEM": "Clique na imagem para definir a origem do sistema cartesiano.",
            "QUADRANTE": "Clique na imagem para definir um ponto no quadrante positivo."
        }

        self.lbl_instrucao.config(
            text=textos.get(modo, "Clique na imagem para definir o ponto."),
            fg="red"
        )

    def atualizar_variaveis_pontos(self):
        def fmt(pt):
            if pt is None:
                return "não definido"
            return f"({pt[0]}, {pt[1]})"

        self.var_ponto_escala_1.set(fmt(self.pontos_escala[0]))
        self.var_ponto_escala_2.set(fmt(self.pontos_escala[1]))
        self.var_origem.set(fmt(self.pontos_sistema[0]))
        self.var_quadrante.set(fmt(self.pontos_sistema[1]))

    # ============================================================
    # EXIBIÇÃO
    # ============================================================

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

            if self.estado_atual == "CONFIGURANDO" and self.mouse_pos_frame is not None:
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
        for i, pt in enumerate(self.pontos_escala):
            if pt is None:
                continue
            cv2.circle(frame, pt, 5, (0, 0, 255), -1)
            cv2.putText(
                frame, f"E{i + 1}", (pt[0] + 8, pt[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA
            )

        origem = self.pontos_sistema[0]
        if origem is not None:
            cv2.circle(frame, origem, 6, (0, 255, 255), -1)
            cv2.putText(
                frame, "O", (origem[0] + 8, origem[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA
            )

        q1 = self.pontos_sistema[1]
        if q1 is not None:
            cv2.circle(frame, q1, 6, (0, 255, 0), -1)
            cv2.putText(
                frame, "Q+", (q1[0] + 8, q1[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA
            )

    # ============================================================
    # CLIQUE E MOUSE
    # ============================================================

    def obter_pixel_do_evento(self, event):
        if not hasattr(self, "foto"):
            return None

        largura_imagem = self.foto.width()
        altura_imagem = self.foto.height()

        espaco_x = (self.lbl_video.winfo_width() - largura_imagem) // 2
        espaco_y = (self.lbl_video.winfo_height() - altura_imagem) // 2

        clique_x = event.x - espaco_x
        clique_y = event.y - espaco_y

        if not (0 <= clique_x <= largura_imagem and 0 <= clique_y <= altura_imagem):
            return None

        x_real = int(clique_x / self.escala_tela)
        y_real = int(clique_y / self.escala_tela)

        return x_real, y_real

    def clique_mouse(self, event):
        ponto = self.obter_pixel_do_evento(event)
        if ponto is None:
            return

        x_real, y_real = ponto

        if self.estado_atual == "CONFIGURANDO":
            if self.modo_captura_config == "ESCALA_1":
                self.pontos_escala[0] = ponto

            elif self.modo_captura_config == "ESCALA_2":
                self.pontos_escala[1] = ponto

            elif self.modo_captura_config == "ORIGEM":
                self.pontos_sistema[0] = ponto

            elif self.modo_captura_config == "QUADRANTE":
                self.pontos_sistema[1] = ponto

            else:
                return

            self.modo_captura_config = None
            self.atualizar_variaveis_pontos()
            self.lbl_instrucao.config(
                text="Ponto definido. Continue configurando ou clique em Processar frames.",
                fg="blue"
            )
            self.mostrar_frame()

        elif self.estado_atual == "VISUALIZANDO":
            self.registrar_marcacao_frame_atual(x_real, y_real)
            self.mostrar_frame()

    def limpar_posicao_mouse(self, event=None):
        self.lbl_status.config(text="Mouse: --")
        self.mouse_pos_frame = None

        if self.estado_atual in ["CONFIGURANDO", "VISUALIZANDO"]:
            self.mostrar_frame()

    def pixel_para_coordenadas(self, x_pixel, y_pixel):
        if self.origem_sistema is None or self.pixels_por_unidade is None or self.pixels_por_unidade <= 0:
            return None

        x0, y0 = self.origem_sistema

        x_coord = ((x_pixel - x0) / self.pixels_por_unidade) * self.sinal_x
        y_coord = ((y_pixel - y0) / self.pixels_por_unidade) * self.sinal_y

        return x_coord, y_coord

    def atualizar_posicao_mouse(self, event):
        ponto = self.obter_pixel_do_evento(event)

        if ponto is None:
            self.lbl_status.config(text="Mouse: fora da imagem")
            if self.mouse_pos_frame is not None:
                self.mouse_pos_frame = None
                if self.estado_atual in ["CONFIGURANDO", "VISUALIZANDO"]:
                    self.mostrar_frame()
            return

        x_real, y_real = ponto
        self.mouse_pos_frame = (x_real, y_real)

        coords = self.pixel_para_coordenadas(x_real, y_real)

        if coords is None:
            self.lbl_status.config(text=f"Mouse (pixel): x = {x_real}, y = {y_real}")
        else:
            x_coord, y_coord = coords
            self.lbl_status.config(
                text=f"Mouse: x = {x_coord:.2f} | y = {y_coord:.2f}"
            )

        if self.estado_atual in ["CONFIGURANDO", "VISUALIZANDO"]:
            self.mostrar_frame()

    # ============================================================
    # DESENHOS
    # ============================================================

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

        cx = (x_mouse - x1) * fator
        cy = (y_mouse - y1) * fator

        cv2.line(lupa, (cx, 0), (cx, lupa.shape[0] - 1), (255, 255, 255), 1)
        cv2.line(lupa, (0, cy), (lupa.shape[1] - 1, cy), (255, 255, 255), 1)
        cv2.line(lupa, (cx, 0), (cx, lupa.shape[0] - 1), (0, 0, 0), 1)
        cv2.line(lupa, (0, cy), (lupa.shape[1] - 1, cy), (0, 0, 0), 1)

        h_lupa, w_lupa = lupa.shape[:2]

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
        texto = f"{tempo_seg:.3f} s".replace(".", ",")

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

        k = 1
        while True:
            x = x0 + k * sinal_x * pixels_por_unidade
            if not (0 <= x < larg):
                break
            x_int = int(round(x))
            cv2.line(frame, (x_int, 0), (x_int, alt), azul, espessura_grade)

            if k % 5 == 0:
                if 0 <= y0 < alt:
                    cv2.line(frame, (x_int, y0 - tamanho_traco), (x_int, y0 + tamanho_traco), preto, 2)

                y_texto = y0 - 8 if y0 > 20 else y0 + 18
                self.escrever_texto_contornado(
                    frame, str(k), (x_int + 2, int(y_texto)),
                    escala=0.45, cor_texto=preto
                )
            k += 1

        k = 1
        while True:
            x = x0 - k * sinal_x * pixels_por_unidade
            if not (0 <= x < larg):
                break
            x_int = int(round(x))
            cv2.line(frame, (x_int, 0), (x_int, alt), azul, espessura_grade)

            if k % 5 == 0:
                if 0 <= y0 < alt:
                    cv2.line(frame, (x_int, y0 - tamanho_traco), (x_int, y0 + tamanho_traco), preto, 2)

                y_texto = y0 - 8 if y0 > 20 else y0 + 18
                self.escrever_texto_contornado(
                    frame, str(-k), (x_int + 2, int(y_texto)),
                    escala=0.45, cor_texto=preto
                )
            k += 1

        k = 1
        while True:
            y = y0 + k * sinal_y * pixels_por_unidade
            if not (0 <= y < alt):
                break
            y_int = int(round(y))
            cv2.line(frame, (0, y_int), (larg, y_int), azul, espessura_grade)

            if k % 5 == 0:
                if 0 <= x0 < larg:
                    cv2.line(frame, (x0 - tamanho_traco, y_int), (x0 + tamanho_traco, y_int), preto, 2)

                x_texto = x0 + 6 if x0 < larg - 50 else x0 - 35
                self.escrever_texto_contornado(
                    frame, str(k), (int(x_texto), y_int - 3),
                    escala=0.45, cor_texto=preto
                )
            k += 1

        k = 1
        while True:
            y = y0 - k * sinal_y * pixels_por_unidade
            if not (0 <= y < alt):
                break
            y_int = int(round(y))
            cv2.line(frame, (0, y_int), (larg, y_int), azul, espessura_grade)

            if k % 5 == 0:
                if 0 <= x0 < larg:
                    cv2.line(frame, (x0 - tamanho_traco, y_int), (x0 + tamanho_traco, y_int), preto, 2)

                x_texto = x0 + 6 if x0 < larg - 50 else x0 - 35
                self.escrever_texto_contornado(
                    frame, str(-k), (int(x_texto), y_int - 3),
                    escala=0.45, cor_texto=preto
                )
            k += 1

        if 0 <= x0 < larg:
            cv2.line(frame, (x0, 0), (x0, alt), preto, espessura_eixos)

        if 0 <= y0 < alt:
            cv2.line(frame, (0, y0), (larg, y0), preto, espessura_eixos)

        cv2.circle(frame, (x0, y0), 5, preto, -1)
        self.escrever_texto_contornado(
            frame, "0", (x0 + 6, y0 - 6),
            escala=0.5, cor_texto=preto
        )

    # ============================================================
    # MARCAÇÕES FINAIS
    # ============================================================

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

        cv2.circle(frame, (x_pixel, y_pixel), 6, (255, 255, 255), -1)
        cv2.circle(frame, (x_pixel, y_pixel), 8, (0, 0, 0), 1)

        texto = f"({tempo_seg:.3f}, {x_coord:.2f}, {y_coord:.2f})".replace(".", ",")

        alt, larg, _ = frame.shape

        x_texto = x_pixel + 8
        y_texto = y_pixel + 22

        if x_texto > larg - 220:
            x_texto = max(10, x_pixel - 200)

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

    # ============================================================
    # EXPORTAÇÃO
    # ============================================================

    def exportar_resultados(self, silencioso=False):
        if not self.frames_processados or not self.pasta_resultados:
            if not silencioso:
                messagebox.showwarning("Atenção", "Ainda não há resultados processados para exportar.")
            return

        try:
            for numero_original, frame_base in self.frames_processados:
                frame_final = self.obter_frame_com_marcacao(numero_original, frame_base)
                caminho_saida = os.path.join(self.pasta_resultados, f"Frame_{numero_original:04d}.jpg")
                cv2.imwrite(caminho_saida, frame_final)

            if not silencioso:
                messagebox.showinfo(
                    "Exportação concluída",
                    f"Os frames foram exportados/atualizados em:\n\n{self.pasta_resultados}"
                )
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar os resultados:\n\n{e}")

    # ============================================================
    # PROCESSAMENTO
    # ============================================================

    def processar_analise(self):
        if self.cap is None:
            messagebox.showerror("Erro", "Selecione um vídeo primeiro.")
            return

        try:
            num_offset = int(self.var_frames_offset.get())
            if num_offset < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erro", "Digite um número inteiro válido para frames antes/depois.")
            return

        try:
            self.pico_frame = int(self.var_pico_frame.get())
        except ValueError:
            messagebox.showerror("Erro", "Defina corretamente o frame central.")
            return

        if not (0 <= self.pico_frame < self.total_frames):
            messagebox.showerror("Erro", "O frame central está fora do intervalo do vídeo.")
            return

        if self.pontos_escala[0] is None or self.pontos_escala[1] is None:
            messagebox.showerror("Erro", "Defina os dois pontos da escala.")
            return

        if self.pontos_sistema[0] is None or self.pontos_sistema[1] is None:
            messagebox.showerror("Erro", "Defina a origem e o ponto do quadrante positivo.")
            return

        try:
            distancia_real = float(self.var_distancia_real.get().replace(",", "."))
            if distancia_real <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erro", "Digite uma distância conhecida válida em cm.")
            return

        try:
            self.frame_t0_ref = int(self.var_t0_frame.get())
            self.frame_tf_ref = int(self.var_tf_frame.get())
            self.tempo_t0_ref = float(self.var_t0_tempo.get().replace(",", "."))
            self.tempo_tf_ref = float(self.var_tf_tempo.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Erro", "Defina corretamente os frames e tempos de t0 e tf.")
            return

        if self.frame_t0_ref == self.frame_tf_ref:
            messagebox.showerror("Erro", "Os frames de t0 e tf não podem ser iguais.")
            return

        delta_frames = self.frame_tf_ref - self.frame_t0_ref
        dt_por_frame = (self.tempo_tf_ref - self.tempo_t0_ref) / delta_frames

        if dt_por_frame <= 0:
            messagebox.showerror(
                "Erro",
                "A calibração temporal ficou inválida.\n\nVerifique se tf > t0 e se o frame de tf vem depois do frame de t0."
            )
            return

        self.dt_por_frame = dt_por_frame

        (x1, y1), (x2, y2) = self.pontos_escala
        distancia_pixels = math.hypot(x2 - x1, y2 - y1)

        if distancia_pixels == 0:
            messagebox.showerror("Erro", "Os dois pontos da escala não podem coincidir.")
            return

        pixels_por_unidade = distancia_pixels / distancia_real

        if pixels_por_unidade <= 0:
            messagebox.showerror("Erro", "Não foi possível calcular a escala.")
            return

        origem = self.pontos_sistema[0]
        ponto_q1 = self.pontos_sistema[1]

        if ponto_q1[0] == origem[0] or ponto_q1[1] == origem[1]:
            messagebox.showerror(
                "Erro",
                "O ponto do quadrante positivo não pode estar alinhado horizontalmente ou verticalmente com a origem."
            )
            return


        sinal_x = 1 if ponto_q1[0] > origem[0] else -1
        sinal_y = 1 if ponto_q1[1] > origem[1] else -1

        # =========================
        # Correção de paralaxe
        # =========================
        try:
            D = float(self.var_D.get().replace(",", "."))
            d = float(self.var_d.get().replace(",", "."))

            if d <= 0 or D <= d:
                raise ValueError

            self.fator_paralaxe = (D - d) / d

        except ValueError:
            messagebox.showerror(
                "Erro",
                "Paralaxe inválida.\n\n"
                "Condições:\n"
                "- D > d > 0\n"
                "- valores numéricos válidos"
            )
            return

        # Escala espacial corrigida pela paralaxe
        self.pixels_por_unidade = pixels_por_unidade / self.fator_paralaxe
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
                pixels_por_unidade=self.pixels_por_unidade
            )

            tempo_seg = self.obter_tempo_do_frame(f)
            self.desenhar_cronometro(frame, tempo_seg)

            self.frames_processados.append((f, frame.copy()))

        self.exportar_resultados(silencioso=True)

        self.estado_atual = "VISUALIZANDO"
        self.modo_captura_config = None
        self.mouse_pos_frame = None

        self.bloquear_painel_configuracao()
        self.btn_exportar.config(state=tk.NORMAL)

        self.lbl_instrucao.config(
            text="Processado. Use as setas para navegar. Clique no frame para marcar (t, x, y).",
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