"""Elementos visuais reutilizados nas páginas e desenho do gráfico."""
import math
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QPainterPath
from PySide6.QtWidgets import (
    QWidget, QLabel, QFrame, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView,
)


def rotulo(texto, nome=None):
    label = QLabel(texto)
    label.setWordWrap(nome not in ('eyebrow', 'badge', 'truncamento', 'arredondamento'))
    label.setTextFormat(Qt.PlainText)
    if nome:
        label.setObjectName(nome)
    return label


def cartao():
    frame = QFrame()
    frame.setObjectName('card')
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(22, 20, 22, 20)
    layout.setSpacing(14)
    return frame, layout


def tabela(colunas):
    widget = QTableWidget(0, len(colunas))
    widget.setHorizontalHeaderLabels(colunas)
    widget.setAlternatingRowColors(True)
    widget.setEditTriggers(QTableWidget.NoEditTriggers)
    widget.verticalHeader().hide()
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    widget.setMinimumHeight(215)
    widget.setShowGrid(False)
    widget.setSelectionBehavior(QTableWidget.SelectRows)
    widget.setWordWrap(True)
    return widget


def preencher(widget, linhas):
    widget.setRowCount(len(linhas))
    for i, linha in enumerate(linhas):
        for j, valor in enumerate(linha):
            item = QTableWidgetItem(str(valor))
            item.setToolTip(str(valor))
            if j > 0:
                item.setFont(QFont('DejaVu Sans Mono', 10))
            if str(valor) in ('truncar', 'arredondar'):
                item.setForeground(QColor('#2563eb' if valor == 'truncar' else '#7c3aed'))
            widget.setItem(i, j, item)
    widget.resizeRowsToContents()


class GraficoErros(QWidget):
    """Gráfico ilustrativo; floats são usados só na pintura, nunca no cálculo."""
    def __init__(self):
        super().__init__()
        self.series = []
        self.decimais = []
        self.setMinimumHeight(240)

    def definir(self, resultados):
        self.decimais = [p['erro_absoluto'] for r in resultados for p in r['passos']]
        self.series = [[float(p['erro_absoluto']) for p in r['passos']] for r in resultados]
        self.update()

    def paintEvent(self, evento):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        left, top, width, height = 85, 16, self.width() - 110, self.height() - 55
        painter.setPen(QColor('#596b85'))
        if not self.series:
            painter.drawText(self.rect(), Qt.AlignCenter, 'Execute uma sequência para visualizar os erros.')
            return
        valores = [v for serie in self.series for v in serie]
        if not all(math.isfinite(v) for v in valores) or (not any(valores) and any(
                p != 0 for p in self.decimais)):
            painter.drawText(self.rect(), Qt.AlignCenter, 'Magnitude fora da escala do gráfico. Consulte a tabela.')
            return
        maximo = max(valores) or 1
        for i in range(5):
            y = top + height * i / 4
            painter.setPen(QPen(QColor('#e4eaf3'), 1))
            painter.drawLine(left, int(y), left + width, int(y))
            painter.setPen(QColor('#596b85'))
            painter.drawText(0, int(y + 5), f'{maximo * ((4-i)/4):.2g}')
        for numero, (serie, cor) in enumerate(zip(self.series, ('#2563eb', '#7c3aed'))):
            linha = QPen(QColor(cor), 2.6)
            if numero == 1:
                linha.setStyle(Qt.DashLine)
            painter.setPen(linha)
            pontos = [(left + width * i / max(1, len(serie)-1), top + height * (1-v/maximo))
                      for i, v in enumerate(serie)]
            if numero == 0 and len(pontos) > 1:
                area = QPainterPath()
                area.moveTo(pontos[0][0], top + height)
                for x, y in pontos:
                    area.lineTo(x, y)
                area.lineTo(pontos[-1][0], top + height)
                area.closeSubpath()
                painter.fillPath(area, QColor(37, 99, 235, 14))
            for a, b in zip(pontos, pontos[1:]):
                painter.drawLine(int(a[0]), int(a[1]), int(b[0]), int(b[1]))
            painter.setBrush(QColor(cor))
            for x, y in pontos:
                painter.drawEllipse(int(x)-2, int(y)-2, 4, 4)
        painter.setPen(QColor('#596b85'))
        painter.drawText(left, top + height + 24, '1')
        painter.drawText(left + width - 25, top + height + 24, str(len(self.series[0])))
        painter.drawText(left + width//2 - 30, top + height + 24, 'Termos')


