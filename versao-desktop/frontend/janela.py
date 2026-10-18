"""Janela do simulador: recebe entradas, chama o backend e exibe os resultados."""
import sys
from pathlib import Path
from decimal import DecimalException
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QCheckBox,
    QStackedWidget, QFrame, QFileDialog, QScrollArea, QBoxLayout,
)
from backend.calculos import calcular, comparar_sequencia
from frontend.apresentacao import formatar_erro_relativo, exportar_sequencia
from frontend.componentes import rotulo, cartao, tabela, preencher, GraficoErros


class JanelaSimulador(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Precisão • Simulador de erros numéricos')
        self.resize(1320, 900)
        self.setMinimumSize(960, 700)
        self.ultimo_resultado = None
        self.ultima_sequencia = None
        self.setStyleSheet(Path(__file__).with_name('estilo.qss').read_text(encoding='utf-8'))
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(225)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(20, 32, 20, 24)
        nav.addWidget(rotulo('∑  Precisão', 'brand'))
        nav.addWidget(rotulo('Laboratório de cálculo numérico'))
        nav.addSpacing(34)
        nav.addWidget(rotulo('EXPLORAR', 'navCaption'))
        self.paginas = QStackedWidget()
        self.botoes = []
        for indice, titulo in enumerate(('01   Calculadora', '02   Somas sucessivas', '03   Exemplos do projeto', '04   Como funciona')):
            botao = QPushButton(titulo)
            botao.setCheckable(True)
            botao.clicked.connect(lambda checked=False, i=indice: self.navegar(i))
            nav.addWidget(botao)
            self.botoes.append(botao)
        nav.addStretch()
        nav.addWidget(rotulo('PRECISÃO CONTROLADA', 'navCaption'))
        nav.addWidget(rotulo('Uma operação.\nDiferentes aproximações.'))
        layout.addWidget(sidebar)
        layout.addWidget(self.paginas, 1)
        self.criar_calculadora()
        self.criar_sequencia()
        self.criar_exemplos()
        self.criar_ajuda()
        self.navegar(0)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        # Em janelas menores, empilha os cartões para manter os campos legíveis.
        if hasattr(self, 'colunas_calculadora'):
            direcao = QBoxLayout.TopToBottom if self.width() < 1180 else QBoxLayout.LeftToRight
            self.colunas_calculadora.setDirection(direcao)

    def navegar(self, indice):
        self.paginas.setCurrentIndex(indice)
        for i, botao in enumerate(self.botoes):
            botao.setChecked(i == indice)

    def pagina(self, titulo, descricao):
        conteudo = QWidget()
        conteudo.setObjectName('page')
        layout = QVBoxLayout(conteudo)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(18)
        cabecalho = QHBoxLayout()
        cabecalho.addWidget(rotulo('CÁLCULO NUMÉRICO  /  SIMULADOR', 'eyebrow'))
        cabecalho.addStretch()
        cabecalho.addWidget(rotulo('PRECISÃO LIMITADA', 'badge'))
        layout.addLayout(cabecalho)
        layout.addWidget(rotulo(titulo, 'title'))
        layout.addWidget(rotulo(descricao, 'subtitle'))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(conteudo)
        self.paginas.addWidget(scroll)
        return layout

    def precisao(self):
        spin = QSpinBox()
        spin.setRange(1, 100)
        spin.setValue(4)
        spin.setSuffix(' dígitos')
        return spin

    def criar_calculadora(self):
        layout = self.pagina('Calculadora de precisão', 'Configure os valores e compare a referência com a aproximação da máquina.')
        frame, box = cartao()
        box.addWidget(rotulo('Configure o cálculo', 'section'))
        grid = QGridLayout()
        for coluna in range(2):
            grid.setColumnStretch(coluna, 1)
        self.x, self.y = QLineEdit('0.76545'), QLineEdit('0.76541')
        self.operacao = QComboBox()
        for texto, simbolo in [('Soma (+)', '+'), ('Subtração (−)', '-'), ('Multiplicação (×)', '*'), ('Divisão (÷)', '/')]:
            self.operacao.addItem(texto, simbolo)
        self.operacao.setCurrentIndex(1)
        self.n = self.precisao()
        self.modo = QComboBox()
        self.modo.addItem('Arredondamento', 'arredondar')
        self.modo.addItem('Truncamento', 'truncar')
        for i, (nome, campo) in enumerate([('Valor de x', self.x), ('Valor de y', self.y),
                                         ('Operação', self.operacao), ('Precisão', self.n), ('Método', self.modo)]):
            grid.addWidget(rotulo(nome), (i//2)*2, i%2)
            grid.addWidget(campo, (i//2)*2+1, i%2, 1, 2 if i == 4 else 1)
        box.addLayout(grid)
        self.limitar = QCheckBox('Limitar também os operandos')
        self.limitar.setChecked(True)
        box.addWidget(self.limitar)
        box.addWidget(rotulo('Simula o armazenamento dos valores antes do cálculo.', 'muted'))
        acoes = QVBoxLayout()
        self.calcular_botao = QPushButton('Calcular resultado')
        self.calcular_botao.setObjectName('primary')
        self.calcular_botao.clicked.connect(self.calcular)
        comparar = QPushButton('Comparar os dois métodos')
        comparar.clicked.connect(self.comparar)
        limpar = QPushButton('Limpar')
        limpar.clicked.connect(self.limpar)
        acoes.addWidget(self.calcular_botao)
        acoes.addWidget(comparar)
        acoes.addWidget(limpar)
        box.addLayout(acoes)
        self.erro = rotulo('', 'error')
        self.erro.hide()
        box.addWidget(self.erro)
        colunas = QHBoxLayout()
        self.colunas_calculadora = colunas
        colunas.setSpacing(20)
        colunas.addWidget(frame, 1)
        colunas.setAlignment(frame, Qt.AlignTop)
        resultados, content = cartao()
        content.addWidget(rotulo('RESULTADO APROXIMADO', 'eyebrow'))
        self.resumo = rotulo('—', 'value')
        self.cientifico = rotulo('Preencha os valores e execute o cálculo.', 'muted')
        content.addWidget(self.resumo)
        content.addWidget(self.cientifico)
        self.metricas = tabela(['Métrica', 'Valor'])
        self.metricas.setMinimumHeight(245)
        content.addWidget(self.metricas)
        self.comparacao = tabela(['Método', 'Aproximado', 'Erro absoluto', 'Erro relativo'])
        self.comparacao.hide()
        content.addWidget(self.comparacao)
        colunas.addWidget(resultados, 1)
        colunas.setAlignment(resultados, Qt.AlignTop)
        layout.addLayout(colunas)
        layout.addWidget(rotulo('Ea = |referência − aproximado|     •     Er = Ea / |aproximado|', 'muted'))
        layout.addStretch()
        self.x.returnPressed.connect(self.calcular)
        self.y.returnPressed.connect(self.calcular)

    def argumentos(self):
        return (self.x.text(), self.y.text(), self.operacao.currentData(),
                self.n.value(), self.modo.currentData(), self.limitar.isChecked())

    def calcular(self):
        self.erro.hide()
        try:
            r = calcular(*self.argumentos())
        except (ValueError, DecimalException) as exc:
            self.ultimo_resultado = None
            self.comparacao.hide()
            self.metricas.setRowCount(0)
            self.resumo.setText('Revise os dados do cálculo.')
            self.cientifico.setText('')
            self.mostrar_erro(self.erro, exc)
            return
        self.ultimo_resultado = r
        self.comparacao.hide()
        self.resumo.setText(str(r['aproximado']))
        m, e = r['cientifico_aproximado']
        self.cientifico.setText(f'{m} × 10^{e}  •  {r["modo"]}  •  {r["n_digitos"]} dígitos')
        preencher(self.metricas, [
            ('Valor de referência', r['exato']),
            ('Erro absoluto', r['erro_absoluto']),
            ('Erro relativo', formatar_erro_relativo(r['erro_relativo'])),
            ('Operandos usados', f'{r["x_aprox"]} e {r["y_aprox"]}'),
        ])

    def comparar(self):
        self.calcular()
        if not self.erro.isHidden():
            return
        x, y, operacao, n_digitos, modo_escolhido, limitar = self.argumentos()
        resultados = []
        try:
            for modo in ('truncar', 'arredondar'):
                # O método escolhido já foi calculado; só falta o outro.
                if modo == modo_escolhido:
                    resultado = self.ultimo_resultado
                else:
                    resultado = calcular(x, y, operacao, n_digitos, modo, limitar)
                resultados.append([
                    modo, resultado['aproximado'], resultado['erro_absoluto'],
                    'Indefinido' if resultado['erro_relativo'] is None else formatar_erro_relativo(resultado['erro_relativo']),
                ])
        except (ValueError, DecimalException) as exc:
            self.mostrar_erro(self.erro, exc)
            return
        preencher(self.comparacao, resultados)
        self.comparacao.show()

    def limpar(self):
        self.x.clear()
        self.y.clear()
        self.erro.hide()
        self.metricas.setRowCount(0)
        self.comparacao.hide()
        self.resumo.setText('Novo cálculo')
        self.cientifico.setText('Preencha os valores para começar.')
        self.ultimo_resultado = None
        self.x.setFocus()

    @staticmethod
    def mostrar_erro(label, erro):
        label.setText(str(erro) if isinstance(erro, ValueError) else 'Não foi possível representar esse cálculo. Revise os valores.')
        label.show()

    def criar_sequencia(self):
        layout = self.pagina('Propagação em somas sucessivas', 'Acompanhe cada etapa e veja a evolução do erro acumulado.')
        frame, box = cartao()
        inputs = QGridLayout()
        for coluna in range(3):
            inputs.setColumnStretch(coluna, 1)
        self.termo = QLineEdit('0.56786')
        self.quantidade = QSpinBox()
        self.quantidade.setRange(1, 1000)
        self.quantidade.setValue(10)
        self.n_sequencia = self.precisao()
        for i, (nome, campo) in enumerate([('Valor de cada termo', self.termo), ('Quantidade de termos', self.quantidade), ('Precisão', self.n_sequencia)]):
            inputs.addWidget(rotulo(nome), 0, i)
            inputs.addWidget(campo, 1, i)
        box.addLayout(inputs)
        self.limitar_sequencia = QCheckBox('Limitar também o valor de cada termo')
        box.addWidget(self.limitar_sequencia)
        acoes = QHBoxLayout()
        self.simular_botao = QPushButton('Simular sequência')
        self.simular_botao.setObjectName('primary')
        self.simular_botao.clicked.connect(self.simular)
        self.exportar = QPushButton('Exportar tabela CSV')
        self.exportar.setEnabled(False)
        self.exportar.clicked.connect(self.exportar_csv)
        acoes.addWidget(self.simular_botao)
        acoes.addStretch()
        acoes.addWidget(self.exportar)
        box.addLayout(acoes)
        self.erro_sequencia = rotulo('', 'error')
        self.erro_sequencia.hide()
        box.addWidget(self.erro_sequencia)
        layout.addWidget(frame)
        frame, box = cartao()
        self.total = rotulo('Acompanhe os resultados em cada etapa.', 'section')
        box.addWidget(self.total)
        self.grafico = GraficoErros()
        box.addWidget(self.grafico)
        legenda = QHBoxLayout()
        legenda.addWidget(rotulo('━  Truncamento', 'truncamento'))
        legenda.addWidget(rotulo('┄  Arredondamento', 'arredondamento'))
        legenda.addStretch()
        legenda.addWidget(rotulo('Erro absoluto acumulado', 'muted'))
        box.addLayout(legenda)
        self.tabela_sequencia = tabela(['Termo', 'Referência', 'Truncamento', 'Ea trunc.', 'Arredondamento', 'Ea arred.'])
        self.tabela_sequencia.setMinimumHeight(330)
        box.addWidget(self.tabela_sequencia)
        self.erros_finais = rotulo('O erro acumulado compara cada parcial com o total ideal.', 'muted')
        box.addWidget(self.erros_finais)
        layout.addWidget(frame)

    def simular(self):
        self.erro_sequencia.hide()
        try:
            resultados = comparar_sequencia(self.termo.text(), self.quantidade.value(), self.n_sequencia.value(), self.limitar_sequencia.isChecked())
        except (ValueError, DecimalException) as exc:
            self.exportar.setEnabled(False)
            self.ultima_sequencia = None
            self.tabela_sequencia.setRowCount(0)
            self.grafico.series = []
            self.grafico.update()
            self.total.setText('Revise os dados da sequência.')
            self.erros_finais.setText('')
            self.mostrar_erro(self.erro_sequencia, exc)
            return
        self.ultima_sequencia = resultados
        a, b = resultados
        linhas = [[p['indice'], p['exato'], p['aproximado'], p['erro_absoluto'], q['aproximado'], q['erro_absoluto']]
                  for p, q in zip(a['passos'], b['passos'])]
        preencher(self.tabela_sequencia, linhas)
        self.total.setText(f'Referência: {a["exato"]}  •  Truncamento: {a["aproximado"]}  •  Arredondamento: {b["aproximado"]}')
        self.erros_finais.setText('Er final — truncamento: ' + formatar_erro_relativo(a['erro_relativo'])
                                 + ' | arredondamento: ' + formatar_erro_relativo(b['erro_relativo']))
        self.grafico.definir(resultados)
        self.exportar.setEnabled(True)

    def exportar_csv(self):
        if not self.ultima_sequencia:
            return
        destino, _ = QFileDialog.getSaveFileName(self, 'Salvar resultados', 'propagacao_erros.csv', 'CSV (*.csv)')
        if not destino:
            return
        try:
            exportar_sequencia(destino, self.ultima_sequencia)
            self.statusBar().showMessage(f'Tabela salva em {destino}', 8000)
        except OSError as exc:
            self.mostrar_erro(self.erro_sequencia, ValueError(f'Não foi possível salvar: {exc}'))

    def criar_exemplos(self):
        layout = self.pagina('Exemplos do projeto', 'Carregue os dados do enunciado e compare os resultados com quatro dígitos.')
        for indice, (titulo, descricao) in enumerate([
            ('01  Soma simples', '0.12345 + 0.67890\nCompare como cada método ajusta o resultado.'),
            ('02  Cancelamento subtrativo', '0.76545 − 0.76541\nCom operandos limitados, o arredondamento produz Er = 60%.'),
            ('03  Propagação de erros', 'Dez termos de 0.56786\nObserve o desvio de cada soma em relação ao total ideal.')]):
            frame, box = cartao()
            box.addWidget(rotulo(titulo, 'section'))
            box.addWidget(rotulo(descricao, 'muted'))
            botao = QPushButton('Abrir exemplo')
            botao.clicked.connect(lambda checked=False, i=indice: self.carregar_exemplo(i))
            box.addWidget(botao, alignment=Qt.AlignLeft)
            layout.addWidget(frame)
        layout.addWidget(rotulo('No exemplo 3, o PDF mostra números com cinco dígitos embora peça quatro. A simulação segue quatro dígitos significativos.', 'muted'))
        layout.addStretch()

    def carregar_exemplo(self, indice):
        if indice == 2:
            self.termo.setText('0.56786')
            self.quantidade.setValue(10)
            self.n_sequencia.setValue(4)
            self.limitar_sequencia.setChecked(False)
            self.navegar(1)
            self.simular()
        else:
            self.x.setText('0.12345' if indice == 0 else '0.76545')
            self.y.setText('0.67890' if indice == 0 else '0.76541')
            self.operacao.setCurrentIndex(0 if indice == 0 else 1)
            self.n.setValue(4)
            self.modo.setCurrentIndex(0)
            self.limitar.setChecked(indice == 1)
            self.navegar(0)
            self.comparar()

    def criar_ajuda(self):
        layout = self.pagina('Guia de interpretação', 'Um guia rápido para interpretar a simulação.')
        for titulo, descricao in [
            ('Dígitos significativos', 'São os dígitos contados a partir do primeiro diferente de zero. Com quatro dígitos, 123.456 vira 123.4 por truncamento e 123.5 por arredondamento.'),
            ('Truncamento e arredondamento', 'Truncamento descarta os dígitos excedentes em direção ao zero. Arredondamento escolhe o mais próximo; empates com 5 são resolvidos afastando do zero.'),
            ('Erro absoluto e relativo', 'Ea = |referência − aproximado|. Er = Ea / |aproximado|, conforme o enunciado. Se o aproximado é zero, o erro relativo é indefinido.'),
            ('Referência decimal', 'Os cálculos usam Decimal e pelo menos 50 dígitos de referência. Divisões periódicas continuam aproximadas. O gráfico usa uma escala visual; os valores da tabela preservam os resultados decimais.'),
            ('Entradas e atalhos', 'Aceita ponto ou vírgula decimal e notação científica, como 1e-3. Não use separadores de milhar. Enter em x ou y executa o cálculo. A interface aceita até 100 dígitos de precisão e 1000 termos por sequência.')]:
            frame, box = cartao()
            box.addWidget(rotulo(titulo, 'section'))
            box.addWidget(rotulo(descricao, 'muted'))
            layout.addWidget(frame)
        layout.addStretch()


def iniciar():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle('Fusion')
    janela = JanelaSimulador()
    janela.show()
    return app.exec()

