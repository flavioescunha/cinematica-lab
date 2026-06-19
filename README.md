# Cinemática Lab

**Cinemática Lab** é um aplicativo em Python para análise de movimento a partir de vídeos, desenvolvido com foco em experimentos didáticos de Física, especialmente estudos de cinemática em sala de aula.

O programa permite importar um vídeo, navegar frame a frame, configurar escalas espaciais e temporais, corrigir paralaxe, gerar frames com quadriculado cartesiano e marcar manualmente a posição de um objeto ao longo do tempo.

---

## Objetivo do projeto

O objetivo do **Cinemática Lab** é facilitar a análise experimental de movimentos registrados em vídeo, permitindo que professores e estudantes obtenham, de forma visual e didática, dados do tipo:

```text
(t, x, y)
```

a partir de imagens extraídas de um vídeo.

O aplicativo é especialmente útil para situações como:

- lançamento vertical;
- queda livre;
- movimento de projéteis;
- movimentos filmados em câmera lenta;
- experimentos com cronômetro visível no vídeo;
- atividades de laboratório escolar com régua, fita métrica ou escala visual.

---

## Funcionalidades principais

### Importação de vídeo

O usuário pode selecionar arquivos de vídeo nos formatos:

```text
.mp4
.avi
.mov
```

Após a importação, o vídeo pode ser navegado frame a frame ou por controle deslizante.

---

## Painel de controle lateral

A versão atual conta com um painel lateral de configuração, no qual o usuário define todos os parâmetros antes do processamento:

- frame central da análise;
- quantidade de frames antes e depois do frame central;
- pontos usados para calibração espacial;
- distância real conhecida;
- origem do sistema cartesiano;
- ponto do quadrante positivo;
- frames de referência temporal;
- tempos reais associados aos frames;
- parâmetros de correção de paralaxe.

Após o processamento, o painel de configuração é bloqueado para preservar os parâmetros usados na análise.

---

## Navegação pelos frames

Durante a configuração, o usuário pode navegar pelo vídeo de duas formas:

- usando as setas do teclado;
- usando o controle deslizante no painel lateral.

Isso permite encontrar rapidamente:

- o frame central do movimento;
- os frames de referência temporal;
- os pontos de calibração.

---

## Calibração espacial

A calibração espacial é feita a partir de dois pontos marcados na imagem e de uma distância real conhecida.

Os dois pontos podem estar em qualquer direção. O programa calcula a distância em pixels usando o Teorema de Pitágoras:

```text
distância_pixels = √[(x2 - x1)² + (y2 - y1)²]
```

A partir disso, calcula a escala:

```text
pixels_por_unidade = distância_pixels / distância_real
```

---

## Sistema cartesiano configurável

O usuário define:

1. a origem do sistema cartesiano;
2. um ponto no quadrante positivo.

A partir desses dois pontos, o programa determina automaticamente o sentido positivo dos eixos `x` e `y`.

O sistema é usado para:

- desenhar os eixos cartesianos;
- gerar o quadriculado;
- calcular as coordenadas dos pontos marcados;
- exibir as coordenadas do mouse no rodapé do programa.

---

## Calibração temporal

A calibração temporal pode ser feita a partir de dois frames de referência:

- frame correspondente a `t0`;
- tempo real associado a `t0`;
- frame correspondente a `tf`;
- tempo real associado a `tf`.

O programa calcula:

```text
Δt_por_frame = (tf - t0) / (frame_tf - frame_t0)
```

Essa abordagem permite usar o tempo real mostrado no cronômetro do vídeo, em vez de depender exclusivamente do FPS informado pelo arquivo.

---

## Correção de paralaxe

O programa permite aplicar uma correção de paralaxe considerando a geometria entre:

- a câmera;
- a escala de referência, como uma régua ou fita métrica;
- o objeto em movimento.

O painel inclui os campos:

```text
D = distância da câmera até a gradação
d = distância do objeto até a gradação
```

O fator usado é:

```text
fator_paralaxe = (D - d) / d
```

Esse fator é incorporado à escala espacial, afetando:

- o quadriculado;
- os eixos;
- as coordenadas do mouse;
- as coordenadas dos pontos marcados nos frames.

---

## Quadriculado e eixos

Após o processamento, os frames são exportados com:

- quadriculado azul;
- eixos cartesianos pretos;
- origem marcada;
- numeração dos eixos de 5 em 5 unidades;
- pequenas marcas pretas nos valores numerados;
- cronômetro no canto inferior esquerdo.

A espessura do quadriculado pode ser ajustada diretamente no início do arquivo `.py`:

```python
ESPESSURA_GRADE_AZUL = 1
```

---

## Lupa de precisão

Durante a marcação dos pontos, o programa exibe uma lupa no canto superior esquerdo da imagem.

A lupa amplia a região ao redor do mouse, facilitando a seleção precisa de pontos.

A ampliação pode ser ajustada no início do código:

```python
FATOR_LUPA = 3
RAIO_CAPTURA_LUPA = 20
MARGEM_LUPA = 10
```

---

## Marcação de pontos nos frames processados

Depois que os frames são processados, o usuário pode navegar pelos resultados e clicar sobre o objeto em cada frame.

Para cada clique, o programa registra:

```text
(t, x, y)
```

A marcação aparece na imagem com:

- uma bolinha branca;
- texto branco contornado de preto;
- coordenadas no formato `(t, x, y)`.

Se o usuário clicar novamente no mesmo frame, a marcação anterior é substituída pela nova.

Cada frame mantém sua própria marcação.

---

## Exportação dos resultados

Os frames processados são exportados automaticamente para uma pasta com nome baseado na data e hora do experimento:

```text
Experimento de AAAA-MM-DD HH-MM
```

Os arquivos seguem o padrão:

```text
Frame_0000.jpg
Frame_0001.jpg
Frame_0002.jpg
...
```

Após marcar pontos manualmente nos frames, o usuário pode clicar em:

```text
Exportar resultados
```

para atualizar os arquivos da pasta com as marcações feitas.

---

## Requisitos

O programa foi desenvolvido em Python e utiliza as seguintes bibliotecas:

```text
opencv-python
pillow
tkinter
```

Também utiliza bibliotecas padrão do Python:

```text
os
math
datetime
```

---

## Instalação

Clone o repositório:

```bash
git clone https://github.com/seu-usuario/seu-repositorio.git
```

Entre na pasta do projeto:

```bash
cd seu-repositorio
```

Instale as dependências necessárias:

```bash
pip install opencv-python pillow
```

> Observação: o `tkinter` normalmente já acompanha a instalação padrão do Python em sistemas Windows. Em algumas distribuições Linux, pode ser necessário instalá-lo separadamente.

---

## Como executar

Execute o arquivo Python principal:

```bash
python cinematica_lab_3.py
```

Caso o nome do arquivo seja diferente, use o nome correspondente ao arquivo `.py` incluído no repositório.

---

## Fluxo básico de uso

1. Clique em **Selecionar vídeo**.
2. Use o controle deslizante ou as setas para navegar pelos frames.
3. Defina o **frame central**.
4. Defina a quantidade de frames antes/depois.
5. Marque os dois pontos da escala espacial.
6. Informe a distância real conhecida.
7. Informe os parâmetros de paralaxe `D` e `d`.
8. Defina a origem do sistema cartesiano.
9. Defina um ponto no quadrante positivo.
10. Defina o frame de `t0` e seu tempo real.
11. Defina o frame de `tf` e seu tempo real.
12. Clique em **Processar frames**.
13. Navegue pelos frames processados.
14. Clique no objeto em cada frame para registrar `(t, x, y)`.
15. Clique em **Exportar resultados** para salvar as marcações.

---

## Organização esperada dos arquivos

Um exemplo simples de organização do repositório:

```text
cinematica-lab/
│
├── cinematica_lab_3.py
├── README.md
└── LICENSE
```

Após a execução, o programa criará automaticamente pastas de saída como:

```text
Experimento de 2026-04-22 15-30/
```

contendo os frames exportados.

---

## Possíveis aplicações didáticas

O Cinemática Lab pode ser usado para:

- estudar posição em função do tempo;
- construir tabelas de dados experimentais;
- analisar gráficos de movimento;
- estimar velocidade e aceleração;
- comparar dados reais com modelos teóricos;
- discutir erros experimentais;
- investigar efeitos de paralaxe;
- introduzir análise de vídeo em aulas de Física.

---

## Limitações

Apesar de útil para fins didáticos, o programa possui algumas limitações:

- a precisão depende da qualidade do vídeo;
- erros de paralaxe podem não ser totalmente eliminados em geometrias complexas;
- a correção atual usa um fator geométrico simplificado;
- a marcação do objeto é manual;
- movimentos fora do plano de análise podem gerar erros;
- vídeos com baixa resolução ou muito borrados dificultam a seleção dos pontos.

---

## Sugestões para melhores resultados

Para obter melhores medidas:

- mantenha a câmera fixa;
- filme o mais perpendicular possível ao plano do movimento;
- use boa iluminação;
- deixe a escala de referência visível;
- evite aproximar demais a câmera;
- use um cronômetro visível quando possível;
- marque pontos sempre no mesmo referencial do objeto;
- faça testes com diferentes distâncias para avaliar paralaxe.

---

## Tecnologias utilizadas

- Python
- OpenCV
- Tkinter
- Pillow

---

## Status do projeto

Projeto em desenvolvimento ativo.

Funcionalidades já implementadas:

- importação de vídeo;
- navegação por frames;
- painel lateral de configuração;
- calibração espacial;
- calibração temporal;
- correção de paralaxe;
- quadriculado cartesiano;
- lupa de precisão;
- marcação manual de pontos;
- exportação dos frames processados.

Possíveis melhorias futuras:

- exportação automática de CSV com dados `(t, x, y)`;
- cálculo automático de velocidade e aceleração;
- geração de gráficos;
- rastreamento automático do objeto;
- salvamento e carregamento de configurações do experimento;
- correção por homografia;
- suporte a múltiplos objetos.

---

## Autor

Desenvolvido por:

```text
Flávio E. S. da Cunha
```

Contato:

```text
flavioescunha@gmail.com
```

---

## Licença

Este projeto pode ser distribuído conforme a licença definida no repositório.

Caso ainda não exista uma licença, recomenda-se adicionar um arquivo `LICENSE` ao projeto.
