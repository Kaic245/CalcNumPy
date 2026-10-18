# Simulador de Propagação de Erros Numéricos

Projeto de Cálculo Numérico com calculadora de precisão limitada, comparação entre
truncamento e arredondamento e acompanhamento do erro em somas sucessivas.

## Executar

O ambiente virtual `.venv` já está instalado neste computador:

```bash
.venv/bin/python main.py
```

O menu de terminal e os exemplos também funcionam sem instalar PySide6:

```bash
python3 main.py --cli
python3 main.py --exemplos
```

Em outro computador, use Python 3.10+ e recrie o ambiente:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Cada pasta Python tem um `__init__.py` para identificá-la como pacote.
**O backend não importa o frontend nem o PySide6.** A janela e o terminal chamam
as mesmas funções, e somente a apresentação transforma os resultados em textos,
tabelas e gráficos. Não há classes, fábricas, controladores ou camadas de serviço
na lógica numérica: são funções, dicionários, condicionais e um laço de somas.


Exemplo de uso do backend, sem abrir uma janela:

```python
from backend.calculos import calcular

resultado = calcular('0.76545', '0.76541', '-', 4, 'arredondar', True)
print(resultado['aproximado'])    # 0.0001000, equivalente a 0.0001
print(resultado['erro_relativo']) # 0.6, equivalente a 60%
```

