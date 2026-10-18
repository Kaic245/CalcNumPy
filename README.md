# CalcNumPy 🧮

> **Simulador de Máquina Hipotética de Precisão Finita e Análise de Erros Numéricos**
> 
> Projeto da **Unidade 1 (Teoria de Erros)** — Disciplina de Cálculo Numérico  
> Universidade Federal do Vale do São Francisco (Univasf) — 2026.2

---

## 📌 Sobre o Projeto

O **CalcNumPy** é um sistema computacional e aplicativo interativo desenvolvido para simular o comportamento de uma **máquina hipotética com precisão limitada a $n$ dígitos**. O projeto permite visualizar, quantificar e analisar empiricamente:

1. As diferenças entre os métodos de **truncamento** e **arredondamento** (*round half up*).
2. O surgimento e a medição dos **erros absolutos ($E_a$)** e **erros relativos ($E_r$)**.
3. O fenômeno da perda de dígitos significativos por **cancelamento subtrativo**.
4. A **propagação e acúmulo de erros** numéricos em computações sequenciais.

A solução conta com uma interface gráfica desenvolvida em **Streamlit**, um motor matemático independente escrito com a biblioteca `Decimal` (garantindo precisão em base 10 pura) e uma suíte rigorosa de testes automatizados.

---

## ✨ Principais Funcionalidades

* **Calculadora Aritmética de Precisão Limitada:** Execução das operações fundamentais ($+$, $-$, $\times$, $\div$) aplicando limitação de $n$ dígitos.
* **Dois Métodos de Descarte:** Suporte a **Truncamento** (corte direto) e **Arredondamento** (*round half up* / $5$ ou mais sobe).
* **Duas Convenções de Precisão:** Ajuste por **Dígitos Significativos** ou por **Casas Decimais**.
* **Dois Modelos de Armazenamento:**
  * *Ajuste no Resultado:* Realiza a operação exata e ajusta a precisão apenas na saída.
  * *Máquina Hipotética Completa:* Armazena os operandos $x$ e $y$ na precisão $n$ antes de operar, simulando registradores de hardware.
* **Detector de Cancelamento Subtrativo:** Identificação automática do fenômeno com indicação da quantidade de ordens de grandeza perdidas.
* **Simulador de Operações Sequenciais:** Análise passo a passo da propagação de erros em laços de repetição, acompanhado de tabelas analíticas e gráficos comparativos.
* **Validação Numérica Automatizada:** Suíte de testes integrados e verificação via amostragem Monte Carlo contra frações exatas.

---

## 📁 Estrutura do Repositório

| Arquivo | Descrição / Responsabilidade |
|---|---|
| `motor_calculo.py` | **Núcleo Matemático:** Implementa normalização, ajuste de precisão, operações exatas com 400 dígitos, cálculo de erros e simulações sequenciais. Não possui dependência de interface. |
| `entrada_saida.py` | **Entrada e Formatação:** Validação de inputs (tratamento de pontos/vírgulas, notação científica) e formatação limpa de saídas numéricas. |
| `app.py` | **Interface Gráfica (Streamlit):** Interface interativa dividida em abas (Calculadora Livre, Casos de Demonstração, Histórico e Documentação). |
| `testes_motor.py` | **Suíte de Testes:** Testes unitários para os exemplos do PDF, validação de casos de borda e comparação com implementação por frações exatas. |
| `requirements.txt` | Especificação de dependências do projeto (`streamlit`). |

### Fluxo de Dependências

```mermaid
flowchart LR
    A["app.py<br/>(Interface Streamlit)"] --> B["entrada_saida.py<br/>(Validação e Formatação)"]
    A --> C["motor_calculo.py<br/>(Núcleo Matemático)"]
    B --> C
    D["testes_motor.py<br/>(Testes Automatizados)"] --> B
    D --> C
