# -*- coding: utf-8 -*-
"""
=====================================================================
TESTES DO MOTOR DE CÁLCULO
Cálculo Numérico • Univasf • Projeto Unidade 1 (Erros)
=====================================================================

Como rodar (no terminal do Codespaces, na pasta do projeto):

    python testes_motor.py

O script:
  1. reproduz os 3 exemplos do enunciado e confere com os valores do PDF;
  2. confere casos em que o `float` do Python erraria (por isso usamos Decimal);
  3. compara o ajuste de precisão com uma IMPLEMENTAÇÃO INDEPENDENTE (usando
     frações exatas) em milhares de números aleatórios;
  4. confere casos especiais (divisão por zero, Er indefinido, entradas inválidas).

Se algum teste falhar, o programa termina com código de erro (útil para o
GitHub Actions). Ele serve também como "plano B" da apresentação: mostra no
terminal o mesmo que o site mostra.
"""

import random
import sys
from decimal import Decimal as D
from fractions import Fraction

from entrada_saida import (formatar, formatar_aprox, formatar_percentual,
                           interpretar_numero, notacao_normalizada)
from motor_calculo import (ErroSimulador, ajustar_precisao,
                           digitos_perdidos_por_cancelamento, normalizar,
                           simular_operacao, simular_operacao_sequencial)

falhas = []


def conferir(descricao, obtido, esperado):
    """Compara obtido x esperado, imprime ✔ / ✘ e registra falhas."""
    ok = obtido == esperado
    if not ok:
        falhas.append(descricao)
    marca = "✔" if ok else "✘"
    detalhe = "" if ok else f"   -> obtido: {obtido!r} | esperado: {esperado!r}"
    print(f"  {marca} {descricao}{detalhe}")


def titulo(texto):
    print("\n" + "=" * 70 + f"\n{texto}\n" + "=" * 70)


# ---------------------------------------------------------------------
# 1. EXEMPLOS DO ENUNCIADO
# ---------------------------------------------------------------------
titulo("EXEMPLO 1 — Soma de 0.12345 + 0.54321 com n = 4 dígitos significativos")
for metodo, aprox_esperado, ea_esperado in (("truncamento", "0.6666", "0.00006"),
                                            ("arredondamento", "0.6667", "0.00004")):
    r = simular_operacao(D("0.12345"), D("0.54321"), "+", 4, metodo, "significativos", False)
    print(f"\n  {metodo.upper()}: exato = {formatar(r['exato'])} | aproximado = {formatar(r['aprox'])} "
          f"| Ea = {formatar(r['ea'])} | Er = {formatar_aprox(r['er'], 6)} ({formatar_percentual(r['er'])})")
    conferir(f"Ex.1 {metodo}: valor aproximado", formatar(r["aprox"]), aprox_esperado)
    conferir(f"Ex.1 {metodo}: erro absoluto", formatar(r["ea"]), ea_esperado)

titulo("EXEMPLO 2 — Cancelamento subtrativo: 0.76545 − 0.76541, n = 4")
r = simular_operacao(D("0.76545"), D("0.76541"), "-", 4, "arredondamento", "significativos", True)
print(f"\n  ARREDONDAMENTO: x_maq = {formatar(r['x_maq'])} | y_maq = {formatar(r['y_maq'])} | "
      f"aproximado = {formatar(r['aprox'])} = {notacao_normalizada(r['aprox'], 4)}")
print(f"  exato = {formatar(r['exato'])} | Ea = {formatar(r['ea'])} | "
      f"Er = {formatar(r['er'])} ({formatar_percentual(r['er'])})")
conferir("Ex.2 arred.: x na máquina", formatar(r["x_maq"]), "0.7655")
conferir("Ex.2 arred.: y na máquina", formatar(r["y_maq"]), "0.7654")
conferir("Ex.2 arred.: resultado aproximado", formatar(r["aprox"]), "0.0001")
conferir("Ex.2 arred.: erro absoluto", formatar(r["ea"]), "0.00006")
conferir("Ex.2 arred.: erro relativo", formatar(r["er"]), "0.6")
conferir("Ex.2 arred.: erro relativo em %", formatar_percentual(r["er"]), "60%")
conferir("Ex.2: cancelamento detectado (ordens de grandeza)", digitos_perdidos_por_cancelamento(r), 4)

rt = simular_operacao(D("0.76545"), D("0.76541"), "-", 4, "truncamento", "significativos", True)
print(f"\n  TRUNCAMENTO: x_maq = {formatar(rt['x_maq'])} | y_maq = {formatar(rt['y_maq'])} | "
      f"aproximado = {formatar(rt['aprox'])}  <- a subtração ficou NULA")
conferir("Ex.2 trunc.: a subtração fica nula", (rt["aprox"] == 0, formatar(rt["ea"])), (True, "0.00004"))
conferir("Ex.2 trunc.: Er indefinido (aproximado = 0)", rt["er"], None)

titulo("EXEMPLO 3 — Somar 0.56786 dez vezes, truncamento, n = 4")
parcela = D("0.56786")
r = simular_operacao_sequencial(None, parcela, "+", 10, 4, "truncamento", "decimais", False)
print("\n  4 CASAS DECIMAIS (como os passos do PDF):")
for p in r["passos"]:
    print(f"    soma {p['passo']}: {formatar(p['anterior'])} + {formatar(p['termo'])} = "
          f"{formatar(p['bruto'])} -> {formatar(p['apos'])}")
print(f"    exato = {formatar(r['exato'])} | final = {formatar(r['final'])} | Ea = {formatar(r['ea'])} "
      f"| Er = {formatar_percentual(r['er'])}")
conferir("Ex.3 (casas decimais): passos do PDF 1.1357, 1.7035, 2.2713",
         [formatar(p["apos"]) for p in r["passos"][:3]], ["1.1357", "1.7035", "2.2713"])
conferir("Ex.3 (casas decimais): resultado final", formatar(r["final"]), "5.6781")
conferir("Ex.3 (casas decimais): erro absoluto", formatar(r["ea"]), "0.0005")
conferir("Ex.3: valor exato 10 × 0.56786", formatar(r["exato"]), "5.6786")
conferir("Ex.3: primeira soma = 0.56786 + 0.56786 = 1.13572",
         (formatar(r["passos"][0]["bruto"]), formatar(r["passos"][0]["termo"])), ("1.13572", "0.56786"))

rs = simular_operacao_sequencial(None, parcela, "+", 10, 4, "truncamento", "significativos", False)
print(f"\n  4 DÍGITOS SIGNIFICATIVOS (item 3.2): passos = {[formatar(p['apos']) for p in rs['passos']]}")
print(f"    final = {formatar(rs['final'])} | Ea = {formatar(rs['ea'])} | Er = {formatar_percentual(rs['er'])}")
conferir("Ex.3 (significativos): resultado final", formatar(rs["final"]), "5.671")
conferir("Ex.3 (significativos): erro absoluto", formatar(rs["ea"]), "0.0076")

ra = simular_operacao_sequencial(None, parcela, "+", 10, 4, "arredondamento", "decimais", False)
print(f"\n  COMPARAÇÃO (4 casas decimais): truncamento final = {formatar(r['final'])} (Ea = {formatar(r['ea'])})"
      f" | arredondamento final = {formatar(ra['final'])} (Ea = {formatar(ra['ea'])})")
conferir("Ex.3 arredondamento (casas decimais): resultado final", formatar(ra["final"]), "5.6789")

# ---------------------------------------------------------------------
# 2. CASOS EM QUE O float ERRARIA
# ---------------------------------------------------------------------
titulo("CASOS EM QUE O float DO PYTHON ERRARIA (e o Decimal acerta)")
casos = [  # (valor, n, método, esperado)
    ("28.4", 4, "truncamento", "28.4"),                 # float dava 28.39
    ("273.9", 4, "truncamento", "273.9"),               # float dava 273.8
    ("789.05", 4, "arredondamento", "789.1"),           # float dava 789.0
    ("1.005", 3, "arredondamento", "1.01"),             # float dava 1.00
    ("1e-20", 4, "truncamento", "1 × 10⁻²⁰"),           # float dava 9.99e-21
    ("999.9999999999999", 4, "truncamento", "999.9"),   # float dava 999.0
    ("-0.76545", 4, "arredondamento", "-0.7655"),
    ("-0.76549", 4, "truncamento", "-0.7654"),
    ("0.99996", 4, "arredondamento", "1"),
]
for valor, n, metodo, esperado in casos:
    conferir(f"{valor} com n={n} ({metodo})",
             formatar(ajustar_precisao(D(valor), n, metodo, "significativos")), esperado)
conferir("normalização 123.45 = 0.12345 × 10³", notacao_normalizada(D("123.45")), "0.12345 × 10³")
conferir("normalização 1000 = 0.1 × 10⁴ (sem erro de log10)", notacao_normalizada(D("1000")), "0.1 × 10⁴")
conferir("mantissa fica em [0.1, 1)", all(D("0.1") <= normalizar(D(v))[1] < 1
                                          for v in ("123.45", "0.00004", "999.99", "1000", "7")), True)

# ---------------------------------------------------------------------
# 3. COMPARAÇÃO COM IMPLEMENTAÇÃO INDEPENDENTE (frações exatas)
# ---------------------------------------------------------------------
titulo("COMPARAÇÃO COM IMPLEMENTAÇÃO INDEPENDENTE (20 000 números aleatórios)")


def referencia(texto, n, metodo, tipo):
    """Mesma regra, mas escrita com Fraction (aritmética exata de racionais)
    e sem usar nada do motor. Serve só para conferir o resultado."""
    v = Fraction(texto)
    sinal = -1 if v < 0 else 1
    v = abs(v)
    if tipo == "significativos":
        e = 0                                   # acha e tal que 10^(e-1) <= v < 10^e
        while v >= Fraction(10) ** e:
            e += 1
        while v < Fraction(10) ** (e - 1):
            e -= 1
        escala = Fraction(10) ** (e - n)
    else:
        escala = Fraction(1, 10 ** n)
    q = v / escala
    q = int(q) if metodo == "truncamento" else int(q + Fraction(1, 2))
    return sinal * q * escala


random.seed(2026)
divergencias = 0
TOTAL = 20000
for _ in range(TOTAL):
    casas = random.randint(0, 8)
    inteiro = random.randint(0, 10 ** random.randint(1, 6))
    frac = random.randint(0, 10 ** casas - 1) if casas else 0
    texto = ("-" if random.random() < 0.3 else "") + (f"{inteiro}.{frac:0{casas}d}" if casas else str(inteiro))
    if random.random() < 0.2:
        texto += "e" + str(random.randint(-30, 30))
    valor = D(texto)
    if valor == 0:
        continue
    n = random.randint(1, 12)
    metodo = random.choice(["truncamento", "arredondamento"])
    tipo = random.choice(["significativos", "decimais"])
    obtido = ajustar_precisao(valor, n, metodo, tipo)
    if Fraction(obtido) != referencia(str(valor), n, metodo, tipo):
        divergencias += 1
conferir(f"{TOTAL} números aleatórios: motor = implementação independente (divergências)", divergencias, 0)

# ---------------------------------------------------------------------
# 4. CASOS ESPECIAIS E ROBUSTEZ
# ---------------------------------------------------------------------
titulo("CASOS ESPECIAIS")
r = simular_operacao(D("0.12345"), D("0.12345"), "+", 4, "arredondamento", "significativos", False)
conferir("modo item 3.2 (só o resultado): 0.12345 + 0.12345 = 0.2469", formatar(r["aprox"]), "0.2469")
r = simular_operacao(D("0.12345"), D("0.12345"), "+", 4, "arredondamento", "significativos", True)
conferir("modo Exemplo 2 (entradas na máquina): 0.12345 + 0.12345 = 0.247", formatar(r["aprox"]), "0.247")

r = simular_operacao(D("0.5"), D("0.5"), "-", 4, "truncamento", "significativos", True)
conferir("0.5 − 0.5: Ea = 0 e Er = 0 (nada a medir)", (r["ea"], r["er"]), (0, 0))
r = simular_operacao(D("1.0000001"), D("1.0"), "-", 4, "arredondamento", "significativos", True)
conferir("aproximado = 0 com Ea > 0: Er indefinido", (r["aprox"] == 0, r["er"]), (True, None))

r = simular_operacao(D(1), D(3), "/", 4, "truncamento", "significativos", False)
conferir("1/3 com n=4 (truncamento) = 0.3333", formatar(r["aprox"]), "0.3333")
conferir("1/3 exato calculado com 400 dígitos", len(r["exato"].as_tuple().digits), 400)

x = "1234567890123456789012345678901234567890123456789"       # 49 dígitos
r = simular_operacao(D(x), D(x), "*", 4, "truncamento", "significativos", False)
conferir("produto de dois números de 49 dígitos sai exato", r["exato"], D(int(x) * int(x)))

for args, nome in (((D(1), D(0), "/", 4, "truncamento", "significativos", True), "1 ÷ 0"),
                   ((D(0), D(0), "/", 4, "truncamento", "significativos", False), "0 ÷ 0"),
                   ((D(1), D("0.00004"), "/", 4, "truncamento", "decimais", True), "Y que vira 0 ao ser guardado")):
    try:
        simular_operacao(*args)
        conferir(f"{nome} deve gerar erro amigável", "não gerou erro", "ErroSimulador")
    except ErroSimulador:
        conferir(f"{nome} gera erro amigável (sem travar)", True, True)

titulo("LEITURA DE NÚMEROS DIGITADOS")
for texto, esperado in (("1,5", "1.5"), (" 0,76545 ", "0.76545"), ("\u22120,5", "-0.5"), (".5", "0.5"),
                        ("1e-5", "0.00001"), ("1.5E+3", "1500"), ("0", "0")):
    conferir(f"aceita {texto!r}", interpretar_numero(texto, "X"), D(esperado))
for texto in ("", "   ", "abc", "NaN", "Infinity", "1.2.3", "1,2,3", "1.234,56", "1e999",
              "1e-101", "1_000", "1 2", "--5", "5-", "1" * 51):
    try:
        interpretar_numero(texto, "X")
        conferir(f"rejeita {texto[:20]!r}", "aceitou", "rejeitou")
    except ErroSimulador:
        conferir(f"rejeita {texto[:20]!r}", True, True)

# ---------------------------------------------------------------------
# RESUMO
# ---------------------------------------------------------------------
titulo("RESUMO")
if falhas:
    print(f"  ✘ {len(falhas)} teste(s) falharam:")
    for f in falhas:
        print("    -", f)
    sys.exit(1)
print("  ✔ Todos os testes passaram.")
