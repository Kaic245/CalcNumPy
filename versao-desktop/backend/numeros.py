"""Conversão, precisão significativa e métricas de erro."""
from decimal import Decimal, InvalidOperation, localcontext, ROUND_DOWN, ROUND_HALF_UP


# Funcao que vai transformar a entrada do usuario em um decimal, preservando os dígitos escritos pelo usuário
def ler_decimal(valor):

    # Se o valor já for um Decimal, apenas retorna
    if isinstance(valor, Decimal):
        numero = valor

    # Se o valor for um inteiro ou float, converte para Decimal
    else:
        texto = str(valor).strip().replace(',', '.')   # substitui virgula por ponto e remove espaços em branco
        
        # validacao da entrada do usuario
        if not texto:
            raise ValueError('Preencha os valores antes de calcular.')
        
        if len(texto) > 200:
            raise ValueError('Use no máximo 200 caracteres por número.')

        
        # Tenta converter o texto em um Decimal
        try:
            numero = Decimal(texto)

        except InvalidOperation:
            raise ValueError('Digite um número decimal válido.') from None

        
        if numero.is_finite() and (
            # Verifica se o expoente do número é maior que 1000 ou menor que -1000
            abs(numero.adjusted()) > 1000 or abs(numero.as_tuple().exponent) > 1000
        ):
            raise ValueError('Use expoentes entre -1000 e 1000.')
    
    # Verifica se o número é finito (não é NaN ou infinito)
    if not numero.is_finite():
        raise ValueError('O número deve ser finito: NaN e infinito não são aceitos.')
    
    # retorna o numero convertido para Decimal e verificado
    return numero


# Funcao que calcula quantos digitos o decimal precisa para o calculo de referencia, Minimo de 50
def precisao_referencia(*valores, minimo=50):

    # Digitos do produto: soma dos dígitos de cada valor
    digitos_produto = sum(len(valor.as_tuple().digits) for valor in valores)

    # Maior casa decimal: posição do dígito mais significativo
    maior_casa = max(valor.adjusted() for valor in valores)

    # menor casa decimal: posição do dígito menos significativo
    menor_casa = min(valor.as_tuple().exponent for valor in valores)


    # retorna o maximo entre o minimo, digitos do produto + 10 e a diferenca entre a maior e menor casa + 10
    return max(minimo, digitos_produto + 10, maior_casa - menor_casa + 10)


# Funcao para validar o numero de digitos e o metodo
def validar_configuracao(n_digitos, modo):

    # verificando se o numero de digitos é um inteiro positivo
    if isinstance(n_digitos, bool) or not isinstance(n_digitos, int) or n_digitos < 1:
        raise ValueError('O número de dígitos deve ser um inteiro positivo.')
    
    if modo == 'truncamento':
        modo = 'truncar'

    elif modo == 'arredondamento':
        modo = 'arredondar'

    # Se nao for truncamento ou arredondamento, levantar erro
    if modo not in ('truncar', 'arredondar'):
        raise ValueError('O método deve ser truncar ou arredondar.')

    # retorna o modo valido
    return modo


# realizando a normalizacao do valor
def normalizar(valor):
    """Exemplo: 123.45 = 0.12345x10³. Zero retorna (0, 0)."""
    
    if valor == 0:
        return valor, 0

    # O método adjusted() retorna o expoente da notação científica, que é a posição do dígito mais significativo. Para normalizar, precisamos ajustar a mantissa para que fique entre 0.1 e 1, e o expoente será ajustado de acordo.
    expoente = valor.adjusted() + 1

    # fazendo a normalização do valor, ajustando a mantissa e o expoente
    with localcontext() as contexto:
        contexto.prec = precisao_referencia(valor)
        mantissa = valor.scaleb(-expoente)     # A função scaleb ajusta o valor deslocando a vírgula decimal, efetivamente normalizando o número para que a mantissa fique entre 0.1 e 1.

    return mantissa, expoente


# funcao para ajustar a precisão do valor, truncando ou arredondando conforme o modo escolhido
def ajustar_precisao(valor, n_digitos, modo):
    """Normaliza → limita a mantissa → reconstrói o número decimal."""
    
    modo = validar_configuracao(n_digitos, modo)  # validando o modo

    valor = ler_decimal(valor)  # convertendo o valor para Decimal

    mantissa, expoente = normalizar(valor)   # Pegando a mantissa e o expoente do valor normalizado

    # localcontext é usado para definir a precisão de cálculo temporariamente, sem afetar o contexto global do Decimal. Aqui, ajustamos a precisão para garantir que a quantização da mantissa seja feita corretamente.
    with localcontext() as contexto:
        contexto.prec = max(n_digitos + 10, len(mantissa.as_tuple().digits) + 10)
        
        # Na mantissa 0.12345, n=4 corresponde à unidade 0.0001.
        unidade = Decimal(1).scaleb(-n_digitos)

        
        if modo == 'truncar':
            regra = ROUND_DOWN       # Corta em direção ao zero, mesmo em negativos.
        else:
            regra = ROUND_HALF_UP    # Empates com 5 são afastados do zero.
        
        # Ajusta a mantissa para a precisão desejada usando quantize, que arredonda ou trunca o número de acordo com a unidade especificada e a regra de arredondamento.
        mantissa = mantissa.quantize(unidade, rounding=regra)

        # retorna o valor reconstruído a partir da mantissa ajustada e do expoente original, usando scaleb para deslocar a vírgula decimal de volta à posição correta.
        return mantissa.scaleb(expoente)


# Funcao para calculo do erro absoluto e relativo
def calcular_erros(referencia, aproximado):
    """Retorna (Ea, Er). Er é None se o denominador aproximado for zero."""

    with localcontext() as contexto:
        contexto.prec = precisao_referencia(referencia, aproximado)
        erro_absoluto = abs(referencia - aproximado)   # calculo do erro absoluto
        
        # Se o valor aproximado for zero, o erro relativo é indefinido
        if aproximado == 0:
            erro_relativo = None
        else:
            # calculo do erro relativo
            erro_relativo = erro_absoluto / abs(aproximado)

    # retorno os dois erros calculados
    return erro_absoluto, erro_relativo
