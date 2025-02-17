import calendar
import threading
from flask import Flask, render_template, request, redirect, send_from_directory, url_for, flash
import mysql.connector
from datetime import datetime, date, timedelta
import time 
import pytz
import schedule
import re

# Módulos padrão do Python
import logging
import datetime  # Importa o módulo completo para evitar conflitos
from datetime import datetime
import requests
import os


# Bibliotecas do Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import NetworkError
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# Reduzir logs de bibliotecas externas (como httpx e Telegram)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.CRITICAL)

# Desativa logs HTTP do Flask no console
if os.getenv("RAILWAY_ENVIRONMENT"):
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

app = Flask(__name__)
app.secret_key = "{k>9IysL&3DQ?cl8rcP4"

# Configuração do banco de dados
config = {
    'user': 'root',
    'password': 'YpiQTLzxzjmnQIfaYasaRSZlKFQLFhQT',
    'host': 'junction.proxy.rlwy.net',
    'port': 48927,
    'database': 'railway'
}


@app.route('/favicon.ico')
def favicon():
    return send_from_directory('icone', 'iconeluka.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/icone/imagemcompartilhamento.jpg')
def imagem_compartilhamento():
    return send_from_directory('icone', 'imagemcompartilhamento.jpg', mimetype='image/jpeg')


# Página inicial: Login pelo celular
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        celular = request.form['celular']

        try:
            conn = mysql.connector.connect(**config)
            cursor = conn.cursor()

            # Verificar se o celular está cadastrado
            query = "SELECT nome FROM clientes WHERE celular = %s"
            cursor.execute(query, (celular,))
            result = cursor.fetchone()

            if result:
                nome_cliente = result[0]

                # Obtendo a data atual em Brasília
                now = datetime.now(pytz.timezone('America/Sao_Paulo'))
                current_date = now.strftime('%Y-%m-%d')  # Formato: '2025-01-20'

                # Obtendo as informações do horário reservado apenas para a data atual
                horario_query = """
                SELECT h.id, h.celular_barbeiro, b.nome, DATE_FORMAT(h.data, '%d/%m/%Y') AS data, TIME_FORMAT(h.horario, '%H:%i') AS horario, p.corte, p.valor
                FROM horarios h
                INNER JOIN barbeiros b ON b.celular = h.celular_barbeiro
                INNER JOIN precos p ON p.id = h.corte_id 
                WHERE h.celular_cliente = %s 
                AND h.status = 'reservado'
                AND h.data = %s
                ORDER BY h.id DESC LIMIT 1
                """
                cursor.execute(horario_query, (celular, current_date))
                horario_info = cursor.fetchone()

                if horario_info:
                    horario_id, celular_barbeiro, nome_barbeiro, data, horario, corte, valor = horario_info
                    
                    return render_template('bemvindo.html', 
                                           nome_cliente=nome_cliente,
                                           nome_barbeiro=nome_barbeiro,
                                           data=data,
                                           horario=horario,
                                           celular_cliente=celular,
                                           horario_id=horario_id,
                                           corte=corte,
                                           valor=valor)
                else:
                    # Redirecionar para bemvindo.html mesmo sem horários reservados
                    return render_template('bemvindo.html', 
                                           nome_cliente=nome_cliente,
                                           celular_cliente=celular,
                                           horario_id=None)  # Sem horário reservado

            else:
                flash("Celular não cadastrado. Por favor, cadastre-se abaixo.", "info")
                return redirect(url_for('cadastro', celular=celular))

        except mysql.connector.Error as err:
            flash(f"Erro ao consultar celular: {err}", "danger")
            return redirect(url_for('login'))

        finally:
            cursor.close()
            conn.close()

    return render_template('login.html')






# Tela de cadastro
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    celular = request.args.get('celular', '')
    if request.method == 'POST':
        celular = request.form['celular']
        nome = request.form['nome']

        try:
            conn = mysql.connector.connect(**config)
            cursor = conn.cursor()
            query = "INSERT INTO clientes (celular, nome) VALUES (%s, %s)"
            cursor.execute(query, (celular, nome))
            conn.commit()
            cursor.close()
            conn.close()

            flash("Cliente cadastrado com sucesso!", "success")
        except mysql.connector.Error as err:
            flash(f"Erro ao cadastrar cliente: {err}", "danger")

        return redirect(url_for('bemvindo', celular_cliente=celular, nome_cliente=nome))

    return render_template('cadastro.html', celular=celular)


# Página de Bem-vindo
@app.route('/bemvindo')
def bemvindo():
    celular_cliente = request.args.get('celular_cliente')
    nome_cliente = request.args.get('nome_cliente')

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Obtendo a data atual em Brasília
        now = datetime.now(pytz.timezone('America/Sao_Paulo'))
        current_date = now.strftime('%Y-%m-%d')  # Formato: '2025-01-20'

        # Obtendo as informações do horário reservado apenas para a data atual
        horario_query = """
        SELECT h.id, h.celular_barbeiro, b.nome, DATE_FORMAT(h.data, '%d/%m/%Y') AS data, TIME_FORMAT(h.horario, '%H:%i') AS horario, p.corte, p.valor
        FROM horarios h
        INNER JOIN barbeiros b ON b.celular = h.celular_barbeiro
        INNER JOIN precos p ON p.id = h.corte_id 
        WHERE h.celular_cliente = %s 
        AND h.status = 'reservado'
        AND h.data = %s
        ORDER BY h.id DESC LIMIT 1
        """
        cursor.execute(horario_query, (celular_cliente, current_date))
        horario_info = cursor.fetchone()

        if horario_info:
            horario_id, celular_barbeiro, nome_barbeiro, data, horario, corte, valor = horario_info
            return render_template('bemvindo.html', 
                                   nome_cliente=nome_cliente,
                                   nome_barbeiro=nome_barbeiro,
                                   data=data,
                                   horario=horario,
                                   corte=corte,
                                   valor=valor,
                                   celular_cliente=celular_cliente,
                                   horario_id=horario_id)
        else:
            return render_template('bemvindo.html', 
                                   nome_cliente=nome_cliente,
                                   celular_cliente=celular_cliente,
                                   horario_id=None)  # Sem horário reservado      
    except mysql.connector.Error as err:
        flash(f"Erro ao consultar horários: {err}", "danger")
        return redirect(url_for('login'))
    finally:
        cursor.close()
        conn.close()









# Função para cancelar o horário reservado
@app.route('/cancelar', methods=['POST'])
def cancelar():
    horario_id = request.form['horario_id']
    celular_cliente = request.form['celular_cliente']

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Atualizar o status, celular e nome do cliente
        query = """
            UPDATE horarios
            SET status = 'disponível', celular_cliente = NULL, nome_cliente = NULL, corte_id = NULL
            WHERE id = %s
        """
        cursor.execute(query, (horario_id,))
        conn.commit()

        # Obter o nome do cliente
        cursor.execute("SELECT nome FROM clientes WHERE celular = %s", (celular_cliente,))
        cliente = cursor.fetchone()
        nome_cliente = cliente[0] if cliente else None

        if not nome_cliente:
            flash("Cliente não encontrado.", "danger")
            return redirect(url_for('login'))

        flash("Horário cancelado com sucesso.", "success")

    except mysql.connector.Error as err:
        flash(f"Erro ao cancelar horário: {err}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('bemvindo', celular_cliente=celular_cliente, nome_cliente=nome_cliente))





# Função para reagendar o horário reservado
@app.route('/reagendar', methods=['POST'])
def reagendar():
    celular_cliente = request.form['celular_cliente']
    horario_id = request.form['horario_id']

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Atualizar o horário atual para "disponível"
        query = """
            UPDATE horarios
            SET status = 'disponível', celular_cliente = NULL, nome_cliente = NULL, corte_id = NULL
            WHERE id = %s
        """
        cursor.execute(query, (horario_id,))
        conn.commit()

    except mysql.connector.Error as err:
        flash(f"Erro ao atualizar o horário anterior: {err}", "danger")
    finally:
        cursor.close()
        conn.close()

    # Redirecionar para a página de barbeiros
    return redirect(url_for('cortes', celular_cliente=celular_cliente))









# Lista de cortes
@app.route('/cortes')
def cortes():
    celular_cliente = request.args.get('celular_cliente')
    nome_cliente = request.args.get('nome_cliente')

    # Obtém o dia da semana em Brasília (0 = Segunda, 1 = Terça, ..., 6 = Domingo)
    dia_semana = datetime.now(pytz.timezone('America/Sao_Paulo')).weekday()

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Consulta para obter todos os cortes e seus IDs
        query = "SELECT id, corte, valor FROM precos"
        cursor.execute(query)
        cortes = cursor.fetchall()

        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        flash(f"Erro ao buscar cortes: {err}", "danger")
        cortes = []

    # Organiza os cortes em grupos de acordo com o dia da semana
    if dia_semana in [1, 2]:  # Terça (1) e Quarta (2)
        grupos = {
            "Combos Promoção": [corte for corte in cortes if corte[0] in [7, 8, 9, 10, 11, 12]],
            "Cortes Promoção": [corte for corte in cortes if corte[0] in [14, 16, 18]],
            "Barba & Sobrancelha": [corte for corte in cortes if corte[0] in [19, 20, 21]],
            "Pinturas & Finalizações": [corte for corte in cortes if corte[0] in [22, 23, 24, 25, 26, 27]]
        }
    else:  # Outros dias
        grupos = {
            "Combos": [corte for corte in cortes if corte[0] in [1, 2, 3, 4, 5, 6]],
            "Cortes Individuais": [corte for corte in cortes if corte[0] in [13, 15, 17]],
            "Barba & Sobrancelha": [corte for corte in cortes if corte[0] in [19, 20, 21]],
            "Pinturas & Finalizações": [corte for corte in cortes if corte[0] in [22, 23, 24, 25, 26, 27]]
        }

    return render_template('cortes.html', grupos=grupos, celular_cliente=celular_cliente, nome_cliente=nome_cliente)







# Lista de barbeiros
@app.route('/barbeiros')
def barbeiros():
    celular_cliente = request.args.get('celular_cliente')
    nome_cliente = request.args.get('nome_cliente')
    corte_id = request.args.get('corte_id')

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        query = "SELECT celular, nome FROM barbeiros WHERE status = 'ativo'"
        cursor.execute(query)
        barbeiros = cursor.fetchall()
        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        flash(f"Erro ao buscar barbeiros: {err}", "danger")
        barbeiros = []

    return render_template('barbeiros.html', barbeiros=barbeiros, celular_cliente=celular_cliente, nome_cliente=nome_cliente, corte_id=corte_id)










# Lista de datas disponíveis para o barbeiro
@app.route('/datas/<celular_barbeiro>')
def datas(celular_barbeiro):
    corte_id = request.args.get('corte_id')

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Obtendo a data atual em Brasília
        current_date = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%Y-%m-%d')  # Formato: '2025-01-20'

        # Query para buscar datas disponíveis
        query = """
        SELECT DISTINCT data 
        FROM horarios 
        WHERE celular_barbeiro = %s AND data >= %s 
        ORDER BY data
        """
        cursor.execute(query, (celular_barbeiro, current_date))
        datas = cursor.fetchall()

        # Formatando as datas para o formato 'DD/MM/YYYY'
        formatted_datas = [
            {
                'original': data[0].strftime('%Y-%m-%d'),  # Formato original para referência
                'formatted': data[0].strftime('%d/%m/%Y')  # Formato 'DD/MM/YYYY'
            }
            for data in datas
        ]

        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        flash(f"Erro ao buscar datas: {err}", "danger")
        formatted_datas = []

    return render_template('datas.html', datas=formatted_datas, celular_barbeiro=celular_barbeiro, corte_id=corte_id)












# Lista de horários do barbeiro para um dia específico
@app.route('/horarios/<celular_barbeiro>/<data>')
def horarios(celular_barbeiro, data):
    celular_cliente = request.args.get('celular_cliente')
    nome_cliente = request.args.get('nome_cliente')
    corte_id = request.args.get('corte_id')

    try:
        # Converter a data recebida no formato YYYY-MM-DD para datetime
        data_obj = datetime.strptime(data, '%Y-%m-%d').date()
        # Formatar a data no formato DD/MM/YYYY
        data_formatada = data_obj.strftime('%d/%m/%Y')

        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Consulta SQL para obter todos os horários do dia, independente da data
        query = """
            SELECT horario, status
            FROM horarios
            WHERE celular_barbeiro = %s 
              AND data = %s 
            ORDER BY horario
        """
        cursor.execute(query, (celular_barbeiro, data))

        horarios_raw = cursor.fetchall()
        cursor.close()
        conn.close()

        # Processar horários
        horarios = [
            (
                f"{(horario.seconds // 3600):02}:{((horario.seconds // 60) % 60):02}",  # Converter timedelta para HH:MM
                status
            )
            for horario, status in horarios_raw
        ]

    except mysql.connector.Error as err:
        flash(f"Erro ao buscar horários: {err}", "danger")
        horarios = []
        data_formatada = data  # Caso ocorra erro, usar a data sem formatar

    return render_template(
        'horarios.html',
        horarios=horarios,
        celular_barbeiro=celular_barbeiro,
        data=data_formatada,  # Enviar a data formatada para o template
        celular_cliente=celular_cliente,
        nome_cliente=nome_cliente,
        corte_id=corte_id
    )





# Reservar horário
@app.route('/reservar', methods=['POST'])
def reservar():
    horario_id = request.form.get('horario_id')
    celular_barbeiro = request.form['celular_barbeiro']
    data = request.form['data']  # Recebida no formato DD/MM/YYYY
    horario = request.form['horario']
    celular_cliente = request.form['celular_cliente']
    corte_id = request.form['corte_id']

    try:
        # Converter a data para o formato YYYY-MM-DD antes de enviar ao banco
        data_formatada = datetime.strptime(data, '%d/%m/%Y').strftime('%Y-%m-%d')

        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Obter o nome do barbeiro
        cursor.execute("SELECT nome FROM barbeiros WHERE celular = %s", (celular_barbeiro,))
        barbeiro = cursor.fetchone()
        nome_barbeiro = barbeiro[0] if barbeiro else None

        if not nome_barbeiro:
            flash("Barbeiro não encontrado.", "danger")
            return redirect(url_for('datas', celular_barbeiro=celular_barbeiro, celular_cliente=celular_cliente))

        # Obter o nome do cliente
        cursor.execute("SELECT nome FROM clientes WHERE celular = %s", (celular_cliente,))
        cliente = cursor.fetchone()
        nome_cliente = cliente[0] if cliente else None

        if not nome_cliente:
            flash("Cliente não encontrado.", "danger")
            return redirect(url_for('login'))

        # Obter informações sobre o corte
        cursor.execute("SELECT corte, valor FROM precos WHERE id = %s", (corte_id,))
        corte_info = cursor.fetchone()

        if not corte_info:
            flash("Tipo de corte não encontrado.", "danger")
            return redirect(url_for('datas', celular_barbeiro=celular_barbeiro, celular_cliente=celular_cliente))

        corte, valor = corte_info

        # Verificar se o horário está disponível
        query = """
            SELECT id
            FROM horarios
            WHERE celular_barbeiro = %s AND data = %s AND horario = %s AND status = 'disponível'
        """
        cursor.execute(query, (celular_barbeiro, data_formatada, horario))
        horario_info = cursor.fetchone()

        if not horario_info:
            flash("Horário desejado não está disponível.", "danger")
            return redirect(url_for('datas', celular_barbeiro=celular_barbeiro, celular_cliente=celular_cliente))

        # Atualizar o status do horário existente
        horario_id = horario_info[0]
        query = """
            UPDATE horarios
            SET celular_barbeiro = %s, data = %s, horario = %s, status = 'reservado', celular_cliente = %s, nome_cliente = %s, corte_id = %s
            WHERE id = %s
        """
        cursor.execute(query, (celular_barbeiro, data_formatada, horario, celular_cliente, nome_cliente, corte_id, horario_id))
        conn.commit()

        cursor.close()
        conn.close()

        flash("Horário agendado com sucesso.", "success")

        return redirect(url_for(
            'bemvindo', 
            celular_cliente=celular_cliente, 
            nome_cliente=nome_cliente, 
            nome_barbeiro=nome_barbeiro, 
            data=data,  # Pode continuar exibindo no formato DD/MM/YYYY para o usuário
            horario=horario, 
            corte=corte, 
            valor=valor
        ))

    except mysql.connector.Error as err:
        flash(f"Erro ao reservar ou reagendar horário: {err}", "danger")
        return redirect(url_for('datas', celular_barbeiro=celular_barbeiro, celular_cliente=celular_cliente))











# Tela de consulta de barbeiros
@app.route('/consultar_barbeiro', methods=['GET', 'POST'])
def consultar_barbeiro():
    if request.method == 'POST':
        celular = request.form['celular']

        try:
            conn = mysql.connector.connect(**config)
            cursor = conn.cursor()

            # Consultar barbeiro pelo celular
            query = "SELECT nome, status, porcentagem, id_telegram FROM barbeiros WHERE celular = %s"
            cursor.execute(query, (celular,))
            barbeiro = cursor.fetchone()

            if barbeiro:
                nome, status, porcentagem, id_telegram = barbeiro
                return render_template(
                    'barbeiro_detalhes.html',
                    celular=celular,
                    nome=nome,
                    status=status,
                    porcentagem=porcentagem,
                    id_telegram=id_telegram
                )
            else:
                return redirect(url_for('cadastrar_barbeiro', celular=celular, message="Barbeiro não encontrado. Cadastre abaixo."))

        except mysql.connector.Error as err:
            flash(f"Erro ao consultar barbeiro: {err}", "danger")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('consultar_barbeiro.html')



# Tela de cadastro de barbeiro
@app.route('/cadastrar_barbeiro', methods=['GET', 'POST'])
def cadastrar_barbeiro():
    celular = request.args.get('celular', '')
    message = request.args.get('message', '')

    if request.method == 'POST':
        celular = request.form['celular']
        nome = request.form['nome']
        id_telegram = request.form['id_telegram']

        try:
            conn = mysql.connector.connect(**config)
            cursor = conn.cursor()

            # Inserir novo barbeiro
            query = "INSERT INTO barbeiros (celular, nome, id_telegram) VALUES (%s, %s, %s)"
            cursor.execute(query, (celular, nome, id_telegram))
            conn.commit()

            flash("Barbeiro cadastrado com sucesso!", "success")
            return redirect(url_for('consultar_barbeiro'))

        except mysql.connector.Error as err:
            flash(f"Erro ao cadastrar barbeiro: {err}", "danger")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('cadastrar_barbeiro.html', celular=celular, message=message)







# Alterar status do barbeiro
@app.route('/alterar_status/<celular>', methods=['POST'])
def alterar_status(celular):
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Consultar o status atual
        query_select = "SELECT status FROM barbeiros WHERE celular = %s"
        cursor.execute(query_select, (celular,))
        result = cursor.fetchone()

        if result:
            status_atual = result[0]
            # Alterar o status (ativo -> inativo ou inativo -> ativo)
            novo_status = "ativo" if status_atual == "inativo" else "inativo"

            query_update = "UPDATE barbeiros SET status = %s WHERE celular = %s"
            cursor.execute(query_update, (novo_status, celular))
            conn.commit()

            flash("Status atualizado com sucesso!", "success")
        else:
            flash("Barbeiro não encontrado.", "danger")

    except mysql.connector.Error as err:
        flash(f"Erro ao alterar status: {err}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    # Redirecionar para a página de detalhes do barbeiro
    return redirect(url_for('consultar_barbeiro'))




# Alterar porcentagem de comissão
@app.route('/alterar_comissao/<celular>', methods=['POST'])
def alterar_comissao(celular):
    nova_porcentagem = request.form['nova_porcentagem']

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Atualizar a porcentagem de comissão
        query = "UPDATE barbeiros SET porcentagem = %s WHERE celular = %s"
        cursor.execute(query, (nova_porcentagem, celular))
        conn.commit()

        flash("Porcentagem de comissão atualizada com sucesso!", "success")
    except mysql.connector.Error as err:
        flash(f"Erro ao atualizar porcentagem de comissão: {err}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for('consultar_barbeiro'))






# Função para selecionar barbeiros com horários agendados no dia atual
@app.route('/selecionar_barbeiro')
def selecionar_barbeiro():
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Obtendo a data atual em Brasília
        now = datetime.now(pytz.timezone('America/Sao_Paulo'))
        current_date = now.strftime('%Y-%m-%d')
        formatted_date = now.strftime('%d/%m/%Y')

        # Query para buscar barbeiros com horários agendados no dia atual
        query = """
        SELECT DISTINCT h.celular_barbeiro, b.nome 
        FROM horarios h 
        INNER JOIN barbeiros b ON b.celular = h.celular_barbeiro 
        WHERE h.data = %s AND h.status = 'reservado'
        """
        cursor.execute(query, (current_date,))
        barbeiros = cursor.fetchall()

        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        flash(f"Erro ao buscar barbeiros: {err}", "danger")
        barbeiros = []

    return render_template('barbeiros_agendados.html', barbeiros=barbeiros, formatted_date=formatted_date)


# Função para selecionar clientes com horários agendados para um barbeiro específico
@app.route('/selecionar_cliente/<celular_barbeiro>')
def selecionar_cliente(celular_barbeiro):
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Obtendo a data atual em Brasília
        now = datetime.now(pytz.timezone('America/Sao_Paulo'))
        current_date = now.strftime('%Y-%m-%d')
        formatted_date = now.strftime('%d/%m/%Y')

        # Query para buscar o nome do barbeiro
        query_barbeiro = "SELECT nome FROM barbeiros WHERE celular = %s"
        cursor.execute(query_barbeiro, (celular_barbeiro,))
        barbeiro = cursor.fetchone()
        nome_barbeiro = barbeiro[0] if barbeiro else "Desconhecido"

        # Query para buscar clientes com horários agendados para o barbeiro selecionado
        query = """
        SELECT h.id, h.celular_barbeiro, TIME_FORMAT(h.horario, '%H:%i') AS horario, h.nome_cliente, p.corte, p.valor 
        FROM horarios h 
        INNER JOIN barbeiros b ON b.celular = h.celular_barbeiro 
        INNER JOIN precos p ON p.id = h.corte_id 
        WHERE h.celular_barbeiro = %s AND h.data = %s AND h.status = 'reservado'
        """
        cursor.execute(query, (celular_barbeiro, current_date))
        clientes = cursor.fetchall()

        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        flash(f"Erro ao buscar clientes: {err}", "danger")
        clientes = []

    return render_template('clientes_agendados.html', clientes=clientes, nome_barbeiro=nome_barbeiro, formatted_date=formatted_date)





# Função para selecionar o pagamento e redirecionar para a confirmação do corte
@app.route('/selecionar_pagamento/<int:horario_id>', methods=['GET', 'POST'])
def selecionar_pagamento(horario_id):
    if request.method == 'POST':
        pagamento = request.form.get('pagamento')
        return redirect(url_for('confirmar_corte', horario_id=horario_id, pagamento=pagamento))
    else:
        return render_template('selecionar_pagamento.html', horario_id=horario_id)






# Função para confirmar o corte
@app.route('/confirmar_corte/<int:horario_id>/<pagamento>', methods=['GET'])
def confirmar_corte(horario_id, pagamento):
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        # Obtendo a data atual em Brasília
        current_date = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%Y-%m-%d')

        # Inserir dados na tabela confirmados
        insert_query = """
        INSERT INTO confirmados (data, horario, celular_barbeiro, celular_cliente, corte, valor, porcentagem, comissao, pagamento)
        SELECT 
            h.data,
            h.horario, 
            h.celular_barbeiro, 
            h.celular_cliente,
            p.corte, 
            p.valor, 
            b.porcentagem,
            CASE 
                WHEN h.corte_id = 24 THEN 20
                WHEN h.corte_id = 25 THEN 30
                WHEN h.corte_id = 22 THEN 10
                ELSE (b.porcentagem / 100) * p.valor 
            END AS comissao,
            %s
        FROM horarios h
        INNER JOIN barbeiros b ON b.celular = h.celular_barbeiro
        INNER JOIN precos p ON p.id = h.corte_id
        WHERE h.id = %s AND h.data = %s AND h.status = 'reservado'
        """
        cursor.execute(insert_query, (pagamento, horario_id, current_date))

        # Recuperar as informações inseridas na tabela confirmados
        select_query = """
        SELECT DATE_FORMAT(cf.data, '%d/%m/%Y') AS data, TIME_FORMAT(cf.horario, '%H:%i') AS horario, 
               b.nome AS barbeiro, c.nome AS cliente, cf.corte, cf.pagamento, cf.valor AS valor_do_corte, cf.comissao AS comissao_do_barbeiro
        FROM confirmados cf
        INNER JOIN barbeiros b ON b.celular = cf.celular_barbeiro
        INNER JOIN clientes c ON c.celular = cf.celular_cliente
        WHERE cf.data = %s AND cf.horario = (SELECT horario FROM horarios WHERE id = %s)
        """
        cursor.execute(select_query, (current_date, horario_id))
        confirmacao = cursor.fetchone()  # Pegar apenas uma linha de resultados
        
        # Consumir quaisquer resultados pendentes
        cursor.fetchall()  # Apenas descarta o restante dos resultados, se houver
        
        # Atualizar o status na tabela horarios
        update_query = """
        UPDATE horarios
        SET status = 'confirmado'
        WHERE id = %s
        """
        cursor.execute(update_query, (horario_id,))

        conn.commit()

        return render_template('confirmacao_corte.html', confirmacao=confirmacao)

    except mysql.connector.Error as err:
        flash(f"Erro ao confirmar corte: {err}", "danger")
        return redirect(url_for('selecionar_barbeiro'))

    finally:
        if cursor is not None:
            cursor.close()  # Fecha o cursor
        if conn.is_connected():
            conn.close()  # Fecha a conexão








# Função para adicionar os horarios
def adicionar_horarios():
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Obtém a data atual em Brasília
        data_atual = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%Y-%m-%d')

        # Consulta para obter barbeiros ativos
        cursor.execute("SELECT celular FROM barbeiros WHERE status = 'ativo'")
        barbeiros = cursor.fetchall()

        for barbeiro in barbeiros:
            celular_barbeiro = barbeiro[0]

            # Gera horários das 08:00 às 20:00 em intervalos de 30 minutos
            horarios = [(celular_barbeiro, data_atual, (datetime(2000, 1, 1, 8, 0) + timedelta(minutes=30 * i)).time()) for i in range(25)]

            # Insere os horários na tabela
            cursor.executemany("""
                INSERT INTO horarios (celular_barbeiro, data, horario, celular_cliente, nome_cliente)
                VALUES (%s, %s, %s, NULL, NULL)
                ON DUPLICATE KEY UPDATE celular_barbeiro = VALUES(celular_barbeiro)
            """, horarios)

        conn.commit()
        cursor.close()
        conn.close()
        print("Horários adicionados com sucesso.")
    except mysql.connector.Error as err:
        print(f"Erro ao adicionar horários: {err}")


def ajustar_horario_execucao():
    # Define o fuso horário de Brasília
    fuso_brasilia = pytz.timezone('America/Sao_Paulo')

    # Obtém o fuso horário do servidor
    fuso_servidor = datetime.now().astimezone().tzinfo

    # Calcula a hora equivalente no servidor para meia-noite em Brasília
    agora_em_brasilia = datetime.now(fuso_brasilia)
    hora_execucao_servidor = agora_em_brasilia.replace(hour=0, minute=0, second=0).astimezone(fuso_servidor).strftime("%H:%M")

    print(f"Agendando execução para {hora_execucao_servidor} no horário do servidor.")

    # Agenda a função no horário correto
    schedule.every().day.at(hora_execucao_servidor).do(adicionar_horarios)












# Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot 
# Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot 
# Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot 
# Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot 
# Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot # Telegram Bot 




# Configurar o token do bot do Telegram
TELEGRAM_TOKEN = "7304207853:AAE7YR1AbSquFBttKrI52vjEjJWic20ahjA"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"


# Configurar o logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



# Função para registrar informações do usuário e do comando
def log_usuario(update, button_name=None):
    user_id = update.effective_user.id  # Obtém o ID do usuário
    user_name = update.effective_user.full_name  # Obtém o nome completo do usuário
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Data/hora formatada
    comando = update.message.text if update.message else "Botão clicado"
    
    if button_name:
        comando = f"Botão {button_name} clicado"

    print(f"Informação {comando} recebido em {data_hora} ID={user_id}, Usuário={user_name}")




# Lista de IDs de autorização total
AUTHORIZED_USER_IDS = [637172689,6416269997,5097049047,7190508925]  # IDs com acesso total

# Lista de IDs de autorização limitada (será preenchida dinamicamente)
LIMITED_ACCESS_USER_IDS = []

# IDs descritos
# ID=637172689 = Márcio Garcia
# ID=6415636681 = Márcio Corporativo
# ID=6416269997 = Lucas Lima
# ID=5097049047 = Rayy
# ID=7190508925 = Walisson Silva



# Função para carregar os IDs dos barbeiros
def carregar_ids_barbeiros():
    try:
        # Conexão com o banco de dados
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)

        # Consulta para obter os IDs dos barbeiros
        cursor.execute("SELECT id_telegram FROM barbeiros where status = 'ativo'")
        barbeiros = cursor.fetchall()

        # Preenche a lista LIMITED_ACCESS_USER_IDS
        global LIMITED_ACCESS_USER_IDS
        LIMITED_ACCESS_USER_IDS = [barbeiro['id_telegram'] for barbeiro in barbeiros]

        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        print(f"Erro ao acessar o banco de dados: {err}")

# Carregar os IDs dos barbeiros ao iniciar o script
carregar_ids_barbeiros()





# Função para o comando /start
async def start(update: Update, context: CallbackContext):
    carregar_ids_barbeiros()  # Atualiza os IDs dos barbeiros antes de processar a solicitação

    user_id = str(update.effective_user.id)  # Converte o user_id para string
    user_name = update.effective_user.full_name  # Obtém o nome completo do usuário

    # Loga a tentativa de acesso
    log_usuario(update)  # Chama a função log_usuario, que já pega user_id e user_name corretamente

    # Verifica se o usuário está autorizado
    if user_id not in map(str, AUTHORIZED_USER_IDS) and user_id not in LIMITED_ACCESS_USER_IDS:
        # Loga a tentativa de acesso de usuário não autorizado
        print(f"Tentativa de acesso de usuário não autorizado: {user_name} (ID: {user_id})")

        # Envia mensagem informando que o usuário não está autorizado
        await update.message.reply_text(
            f"Olá, {user_name}!👋\nVocê não está autorizado a acessar o Bot Luka Barbearia.\n\nID Telegram: {user_id}"
        )
        return

    # Define o menu com base na autorização
    if user_id in LIMITED_ACCESS_USER_IDS:
        # Menu para usuários com acesso limitado
        keyboard = [
            [InlineKeyboardButton("Agendar Horário", url="web-production-9c5e2.up.railway.app")],
            [InlineKeyboardButton("Cortes por Barbeiro", callback_data="cortes_barbeiro")],
            [InlineKeyboardButton("Comissão por Barbeiro", callback_data="comissao_barbeiro")],
        ]
        welcome_message = f"Olá, {user_name}! 👋\nBem-vindo ao *Bot Luka Barbearia*! 💪\n\nAqui estão as opções disponíveis no menu:"
    else:
        # Menu para usuários com acesso total
        keyboard = [
            [InlineKeyboardButton("Agendar Horário", url="web-production-9c5e2.up.railway.app")],
            [InlineKeyboardButton("Cadastrar Barbeiro", url="web-production-9c5e2.up.railway.app/consultar_barbeiro")],
            [InlineKeyboardButton("Confirmar Corte", url="web-production-9c5e2.up.railway.app/selecionar_barbeiro")],
            [InlineKeyboardButton("Lista Barbeiros", callback_data="lista_barbeiro")],
            [InlineKeyboardButton("Cortes por Barbeiro", callback_data="cortes_barbeiro")],
            [InlineKeyboardButton("Comissão por Barbeiro", callback_data="comissao_barbeiro")],
            [InlineKeyboardButton("Ajustar Comissão", callback_data="ajustar_comissao")],
            [InlineKeyboardButton("Faturamento Mês", callback_data="faturamentomes")],
        ]
        welcome_message = f"Olá, {user_name}! 👋\nBem-vindo ao *Bot Luka Barbearia*! 💪\n\nAqui estão as opções disponíveis no menu:"

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Envia a mensagem de boas-vindas com o menu
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode="Markdown"  # Habilita formatação de texto (negrito, itálico, emojis)
    )

# Comando para exibir o menu de comandos com botão
async def menu(update: Update, context: CallbackContext):
    carregar_ids_barbeiros()  # Atualiza os IDs dos barbeiros antes de processar a solicitação

    user_id = str(update.effective_user.id)
    user_name = update.effective_user.full_name

    # Loga a tentativa de acesso
    log_usuario(update)  # Chama a função log_usuario, que já pega user_id e user_name corretamente

    # Verifica se o usuário está autorizado
    if user_id not in map(str, AUTHORIZED_USER_IDS) and user_id not in LIMITED_ACCESS_USER_IDS:
        # Loga a tentativa de acesso de usuário não autorizado
        print(f"Tentativa de acesso de usuário não autorizado ao menu: {user_name} (ID: {user_id})")

        # Envia mensagem informando que o usuário não está autorizado
        await update.message.reply_text(
            f"Olá, {user_name}!👋\nVocê não está autorizado a acessar o Bot Luka Barbearia.\n\nID Telegram: {user_id}"
        )
        return

    # Define o menu com base na autorização
    if user_id in LIMITED_ACCESS_USER_IDS:
        # Menu para usuários com acesso limitado
        keyboard = [
            [InlineKeyboardButton("Agendar Horário", url="web-production-9c5e2.up.railway.app")],
            [InlineKeyboardButton("Cortes por Barbeiro", callback_data="cortes_barbeiro")],
            [InlineKeyboardButton("Comissão por Barbeiro", callback_data="comissao_barbeiro")],
        ]
        message_text = "Escolha uma opção:"
    else:
        # Menu para usuários com acesso total
        keyboard = [
            [InlineKeyboardButton("Agendar Horário", url="web-production-9c5e2.up.railway.app")],
            [InlineKeyboardButton("Cadastrar Barbeiro", url="web-production-9c5e2.up.railway.app/consultar_barbeiro")],
            [InlineKeyboardButton("Confirmar Corte", url="web-production-9c5e2.up.railway.app/selecionar_barbeiro")],
            [InlineKeyboardButton("Lista Barbeiros", callback_data="lista_barbeiro")],
            [InlineKeyboardButton("Cortes por Barbeiro", callback_data="cortes_barbeiro")],
            [InlineKeyboardButton("Comissão por Barbeiro", callback_data="comissao_barbeiro")],
            [InlineKeyboardButton("Ajustar Comissão", callback_data="ajustar_comissao")],
            [InlineKeyboardButton("Faturamento Mês", callback_data="faturamentomes")],
        ]
        message_text = "Escolha uma opção:"

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Verifica se o update possui message ou callback_query
    if update.message:
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    elif update.callback_query:
        query = update.callback_query
        await safe_edit_message(query, message_text, reply_markup)

# Função auxiliar para editar mensagens somente se necessário
async def safe_edit_message(query, new_text, reply_markup=None):
    current_text = query.message.text
    current_markup = query.message.reply_markup

    # Verifica se o texto ou os botões são diferentes
    if current_text == new_text and current_markup == reply_markup:
        return  # Não faz nada se forem iguais

    await query.edit_message_text(text=new_text, reply_markup=reply_markup)







# Função para exibir a lista de barbeiros
async def lista_barbeiro(update: Update, context: CallbackContext):
    query = update.callback_query
    button_name = "Lista Barbeiro"  # Nome do botão
    log_usuario(update, button_name)  # Log para registrar quem clicou no botão

    try:
        # Conexão com o banco de dados
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Consulta no banco
        query_sql = "SELECT celular, nome, status, porcentagem FROM barbeiros"
        cursor.execute(query_sql)
        barbeiros = cursor.fetchall()

        # Verifica se há resultados
        if not barbeiros:
            # Cria botões "Consultar Novamente" e "Menu"
            keyboard = [
                [InlineKeyboardButton("Consultar Novamente", callback_data="lista_barbeiro")],
                [InlineKeyboardButton("Menu", callback_data="menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.message.reply_text("Nenhum dado encontrado.", reply_markup=reply_markup)
            return

        # Formata a mensagem para o usuário
        resposta = "Dados encontrados dos barbeiros: \n\n"
        for celular, nome, status, porcentagem in barbeiros:
            # Ajusta o status com o ícone correspondente
            status_icone = "🟢Ativo" if status.lower() == "ativo" else "🔴Inativo"
            resposta += f"*Celular:* {celular}\n*Nome:* {nome}\n*Status:* {status_icone}\n*Comissão:* {porcentagem}%\n\n"

        # Define os botões "Menu" e "Consultar Novamente"
        keyboard = [
            
                [InlineKeyboardButton("Consultar Novamente", callback_data="lista_barbeiro")],
                [InlineKeyboardButton("Menu", callback_data="menu")],
            
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Envia a mensagem para o usuário com os botões
        await query.message.reply_text(
            resposta,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    except mysql.connector.Error as err:
        await query.message.reply_text(f"Erro ao acessar o banco de dados: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()







def verificar_horario():
    """Verifica se o horário está dentro do permitido (08h às 21h) todos os dias da semana."""
    agora = datetime.now(pytz.timezone('America/Sao_Paulo'))
    hora_atual = agora.hour

    return 8 <= hora_atual < 21  # Permite entre 08h e 21h



def enviar_mensagem(telegram_id, mensagem):
    """Envia a mensagem para o usuário no Telegram."""
    payload = {
        'chat_id': telegram_id,
        'text': mensagem,
        'parse_mode': 'Markdown'
    }
    response = requests.post(TELEGRAM_URL, data=payload)
    return response.status_code == 200

def enviar_mensagem_barbeiro():
    """Monitora a tabela mensagem e envia notificações para mensagens pendentes, dentro do horário permitido."""
    while True:
        if verificar_horario():
            try:
                conn = mysql.connector.connect(**config)
                cursor = conn.cursor(dictionary=True)
                
                cursor.execute("SELECT id, data, horario, nome_barbeiro, nome_cliente, corte, id_telegram FROM mensagem WHERE status = 'pendente'")
                mensagens = cursor.fetchall()
                
                for msg in mensagens:
                    data_formatada = datetime.strptime(str(msg['data']), "%Y-%m-%d").strftime("%d/%m/%Y")
                    horario_formatado = datetime.strptime(str(msg['horario']), "%H:%M:%S").strftime("%H:%M")
                    
                    mensagem_texto = f"""
*✂️ Novo horário agendado! ✂️*\n
E aí, {msg['nome_barbeiro']}, tem serviço marcado! 🎉\n
📅 *Data:* {data_formatada}
⏰ *Horário:* {horario_formatado}
👤 *Cliente:* {msg['nome_cliente']}
✂️ *Corte:* {msg['corte']}\n
Deixa tudo na régua, hein? 📏✂️
                    """
                    
                    if enviar_mensagem(msg['id_telegram'], mensagem_texto):
                        print(f"Mensagem enviada com sucesso para o ID {msg['id_telegram']} {msg['nome_barbeiro']}")
                        cursor.execute("UPDATE mensagem SET status = 'enviado' WHERE id = %s", (msg['id'],))
                        conn.commit()
                
                cursor.close()
                conn.close()
            
            except Exception as e:
                print(f"Erro: {e}")
            
            time.sleep(5)  # Espera 5 segundos antes de rodar novamente
        else:
            if datetime.now(pytz.timezone('America/Sao_Paulo')).hour >= 21:
                time.sleep(12 * 60 * 60)  # Aguarda 12 horas (caso seja após as 20h)
            else:
                time.sleep(60 * 60)  # Aguarda 1 hora se ainda não for 08h

def enviar_mensagem_confirmados():
    """Verifica a tabela confirmados e envia notificações para mensagens pendentes, dentro do horário permitido."""
    while True:
        if verificar_horario():
            try:
                conn = mysql.connector.connect(**config)
                cursor = conn.cursor(dictionary=True)
                
                cursor.execute("""
                    SELECT c.id, c.data, c.horario, b.nome AS nome_barbeiro, cl.nome AS nome_cliente, 
                           c.pagamento, c.corte, c.valor, c.comissao, b.id_telegram   
                    FROM confirmados c
                    INNER JOIN barbeiros b ON b.celular = c.celular_barbeiro 
                    INNER JOIN clientes cl ON cl.celular = c.celular_cliente 
                    WHERE c.status = 'pendente'
                """)
                confirmados = cursor.fetchall()
                
                for conf in confirmados:
                    data_formatada = datetime.strptime(str(conf['data']), "%Y-%m-%d").strftime("%d/%m/%Y")
                    horario_formatado = datetime.strptime(str(conf['horario']), "%H:%M:%S").strftime("%H:%M")
                    
                    mensagem_texto = f"""
*✂️ Corte Realizado! ✂️*

E aí, {conf['nome_barbeiro']} mandou bem demais! 🎉
📅 *Data:* {data_formatada}
⏰ *Horário:* {horario_formatado}
👤 *Cliente:* {conf['nome_cliente']}
✂️ *Corte:* {conf['corte']}
💳 *Pagamento:* {conf['pagamento']}
💵 *Valor:* {conf['valor']}
💰 *Comissão:* {conf['comissao']}

O cliente saiu satisfeito e o caixa agradece!💸
Bora continuar arrasando!💪🔥
                    """
                    
                    # Envia a mensagem para o ID fixo e para o barbeiro
                    ids_destinatarios = [637172689,6416269997]
                    if conf['id_telegram']:
                        ids_destinatarios.append(conf['id_telegram'])
                    
                    for id_dest in ids_destinatarios:
                        if enviar_mensagem(id_dest, mensagem_texto):
                            print(f"Mensagem enviada com sucesso para o ID {id_dest}")
                    
                    # Atualiza o status para 'enviado'
                    cursor.execute("UPDATE confirmados SET status = 'enviado' WHERE id = %s", (conf['id'],))
                    conn.commit()
                
                cursor.close()
                conn.close()
            
            except Exception as e:
                print(f"Erro: {e}")
            
            time.sleep(5)  # Espera 5 segundos antes de rodar novamente
        else:
            if datetime.now(pytz.timezone('America/Sao_Paulo')).hour >= 21:
                time.sleep(12 * 60 * 60)  # Aguarda 12 horas
            else:
                time.sleep(60 * 60)  # Aguarda 1 hora se ainda não for 08h







# Função para exibir os barbeiros
async def cortes_barbeiro(update: Update, context: CallbackContext):
    query = update.callback_query
    button_name = "Cortes por Barbeiro"  # Nome do botão
    log_usuario(update, button_name)  # Log para registrar quem clicou no botão
    user_id = str(update.effective_user.id)  # Converte o user_id para string

    try:
        # Conexão com o banco de dados
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)

        # Consulta para obter os barbeiros
        cursor.execute("SELECT id_telegram, nome FROM barbeiros")
        barbeiros = cursor.fetchall()

        # Verifica se há resultados
        if not barbeiros:
            await query.message.reply_text("Nenhum barbeiro encontrado.")
            return

        # Cria os botões para os barbeiros
        keyboard = []
        for barbeiro in barbeiros:
            if user_id == barbeiro['id_telegram'] or user_id in map(str, AUTHORIZED_USER_IDS):
                keyboard.append([InlineKeyboardButton(barbeiro['nome'], callback_data=f"barbeirocortes_{barbeiro['id_telegram']}")])

        # Verifica se o usuário é um barbeiro e adiciona apenas o seu botão
        if user_id in LIMITED_ACCESS_USER_IDS:
            barbeiro_nome = next(barbeiro['nome'] for barbeiro in barbeiros if barbeiro['id_telegram'] == user_id)
            keyboard = [[InlineKeyboardButton(barbeiro_nome, callback_data=f"barbeirocortes_{user_id}")]]
        elif user_id in map(str, AUTHORIZED_USER_IDS):
            # Adiciona todos os barbeiros para usuários autorizados
            keyboard = [[InlineKeyboardButton(barbeiro['nome'], callback_data=f"barbeirocortes_{barbeiro['id_telegram']}")] for barbeiro in barbeiros]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Envia a mensagem com os botões dos barbeiros
        await query.message.reply_text("Selecione o barbeiro:", reply_markup=reply_markup)

    except mysql.connector.Error as err:
        await query.message.reply_text(f"Erro ao acessar o banco de dados: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Função para exibir os anos disponíveis
async def selecionar_ano_cortes(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = update.effective_user.id
    id_telegram = query.data.split('_')[1]

    try:
        # Conexão com o banco de dados
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)

        # Consulta para obter os anos disponíveis
        cursor.execute("SELECT DISTINCT YEAR(data) AS anocorte FROM confirmados WHERE celular_barbeiro = (SELECT celular FROM barbeiros WHERE id_telegram = %s)", (id_telegram,))
        anos = cursor.fetchall()

        # Verifica se há resultados
        if not anos:
            # Cria botões "Consultar Novamente" e "Menu"
            keyboard = [
                [InlineKeyboardButton("Consultar Novamente", callback_data="cortes_barbeiro")],
                [InlineKeyboardButton("Menu", callback_data="menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.message.reply_text("Nenhum dado encontrado.", reply_markup=reply_markup)
            return

        # Cria os botões para os anos
        keyboard = []
        for ano in anos:
            keyboard.append([InlineKeyboardButton(str(ano['anocorte']), callback_data=f"anocorte_{ano['anocorte']}_{id_telegram}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Envia a mensagem com os botões dos anos
        await query.message.reply_text("Selecione o ano:", reply_markup=reply_markup)

    except mysql.connector.Error as err:
        await query.message.reply_text(f"Erro ao acessar o banco de dados: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Função para exibir os meses disponíveis
async def selecionar_mes_cortes(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = update.effective_user.id
    _, ano, id_telegram = query.data.split('_')

    try:
        # Conexão com o banco de dados
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)

        # Consulta para obter os meses disponíveis
        cursor.execute("SELECT DISTINCT MONTH(data) AS mescortes FROM confirmados WHERE celular_barbeiro = (SELECT celular FROM barbeiros WHERE id_telegram = %s) AND YEAR(data) = %s", (id_telegram, ano))
        meses = cursor.fetchall()

        # Verifica se há resultados
        if not meses:
            await query.message.reply_text("Nenhum mês encontrado.")
            return

        # Cria os botões para os meses em português
        meses_pt = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        keyboard = []
        for mes in meses:
            nome_mes = meses_pt[mes['mescortes'] - 1]
            keyboard.append([InlineKeyboardButton(nome_mes, callback_data=f"mescortes_{mes['mescortes']}_{ano}_{id_telegram}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Envia a mensagem com os botões dos meses
        await query.message.reply_text("Selecione o mês:", reply_markup=reply_markup)

    except mysql.connector.Error as err:
        await query.message.reply_text(f"Erro ao acessar o banco de dados: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()



# Função para exibir os cortes confirmados
async def exibir_cortes(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = update.effective_user.id
    _, mes, ano, id_telegram = query.data.split('_')

    try:
        # Conexão com o banco de dados
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)

        # Consulta para obter os cortes confirmados
        cursor.execute("""
            SELECT c.data, c.horario, b.nome AS nome_barbeiro, cl.nome AS nome_cliente, c.corte, c.pagamento,c.valor, c.comissao 
            FROM confirmados c
            INNER JOIN barbeiros b ON b.celular = c.celular_barbeiro 
            INNER JOIN clientes cl ON cl.celular = c.celular_cliente 
            WHERE b.id_telegram = %s AND YEAR(c.data) = %s AND MONTH(c.data) = %s
            ORDER BY c.data, c.horario
        """, (id_telegram, ano, mes))
        cortes = cursor.fetchall()

        # Verifica se há resultados
        if not cortes:
            await query.message.reply_text("Nenhum corte encontrado.")
            return

        # Meses em português
        meses_pt = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        nome_mes = meses_pt[int(mes) - 1]

        # Formata a mensagem para o usuário
        nome_barbeiro = cortes[0]['nome_barbeiro']
        resposta = f"Segue os cortes do barbeiro {nome_barbeiro} do mês {nome_mes}:\n\n"
        mensagens = []
        for corte in cortes:
            data_formatada = datetime.strptime(str(corte['data']), "%Y-%m-%d").strftime("%d/%m/%Y")
            horario_formatado = datetime.strptime(str(corte['horario']), "%H:%M:%S").strftime("%H:%M")
            mensagens.append(f"*Data:* {data_formatada}\n*Horário:* {horario_formatado}\n*Cliente:* {corte['nome_cliente']}\n*Corte:* {corte['corte']}\n*Pagamento:* {corte['pagamento']}\n*valor:* R$ {corte['valor']}\n*Comissão:* R$ {corte['comissao']}\n\n")

        # Dividir a mensagem em blocos de 20 cortes
        blocos = [mensagens[i:i + 20] for i in range(0, len(mensagens), 20)]

        # Envia a mensagem para o usuário
        for i, bloco in enumerate(blocos):
            resposta_completa = resposta + ''.join(bloco)
            
            # No último bloco, adicionar os botões
            if i == len(blocos) - 1:
                keyboard = [
                    [InlineKeyboardButton("Consultar Novamente", callback_data="cortes_barbeiro")],
                    [InlineKeyboardButton("Menu", callback_data="menu")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_text(
                    resposta_completa,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            else:
                await query.message.reply_text(
                    resposta_completa,
                    parse_mode="Markdown"
                )

    except mysql.connector.Error as err:
        await query.message.reply_text(f"Erro ao acessar o banco de dados: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()










# Função para exibir os barbeiros
async def comissao_barbeiro(update: Update, context: CallbackContext):
    query = update.callback_query
    button_name = "Comissão por Barbeiro"  # Nome do botão
    log_usuario(update, button_name)  # Log para registrar quem clicou no botão
    user_id = str(update.effective_user.id)  # Converte o user_id para string

    try:
        # Conexão com o banco de dados
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)

        # Consulta para obter os barbeiros
        cursor.execute("SELECT id_telegram, nome FROM barbeiros")
        barbeiros = cursor.fetchall()

        # Verifica se há resultados
        if not barbeiros:
            # Cria botões "Consultar Novamente" e "Menu"
            keyboard = [
                [InlineKeyboardButton("Consultar Novamente", callback_data="comissao_barbeiro")],
                [InlineKeyboardButton("Menu", callback_data="menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.message.reply_text("Nenhum dado encontrado.", reply_markup=reply_markup)
            return

        # Cria os botões para os barbeiros
        keyboard = []
        for barbeiro in barbeiros:
            if user_id == barbeiro['id_telegram'] or user_id in map(str, AUTHORIZED_USER_IDS):
                keyboard.append([InlineKeyboardButton(barbeiro['nome'], callback_data=f"barbeirocomissao_{barbeiro['id_telegram']}")])

        # Verifica se o usuário é um barbeiro e adiciona apenas o seu botão
        if user_id in LIMITED_ACCESS_USER_IDS:
            barbeiro_nome = next(barbeiro['nome'] for barbeiro in barbeiros if barbeiro['id_telegram'] == user_id)
            keyboard = [[InlineKeyboardButton(barbeiro_nome, callback_data=f"barbeirocomissao_{user_id}")]]
        elif user_id in map(str, AUTHORIZED_USER_IDS):
            # Adiciona todos os barbeiros para usuários autorizados
            keyboard = [[InlineKeyboardButton(barbeiro['nome'], callback_data=f"barbeirocomissao_{barbeiro['id_telegram']}")] for barbeiro in barbeiros]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Envia a mensagem com os botões dos barbeiros
        await query.message.reply_text("Selecione o barbeiro:", reply_markup=reply_markup)

    except mysql.connector.Error as err:
        await query.message.reply_text(f"Erro ao acessar o banco de dados: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Função para exibir os anos disponíveis
async def selecionar_ano_comissao(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = update.effective_user.id
    id_telegram = query.data.split('_')[1]

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)

        # Verifica se o ID está correto
        cursor.execute("SELECT celular FROM barbeiros WHERE id_telegram = %s", (id_telegram,))
        resultado = cursor.fetchone()

        if not resultado:
            await query.message.reply_text("Erro: ID do barbeiro não encontrado.")
            return

        celular_barbeiro = resultado['celular']

        # Executa a consulta para os anos
        sql = "SELECT DISTINCT YEAR(data) AS anocomissao FROM confirmados WHERE celular_barbeiro = %s"
        
        cursor.execute(sql, (celular_barbeiro,))
        anos = cursor.fetchall()

        if not anos:
            # Cria botões "Consultar Novamente" e "Menu"
            keyboard = [
                [InlineKeyboardButton("Consultar Novamente", callback_data="comissao_barbeiro")],
                [InlineKeyboardButton("Menu", callback_data="menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.message.reply_text("Nenhum dado encontrado.", reply_markup=reply_markup)
            return

        # Cria os botões
        keyboard = []
        for ano in anos:
            keyboard.append([InlineKeyboardButton(str(ano['anocomissao']), callback_data=f"anocomissao_{ano['anocomissao']}_{id_telegram}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.reply_text("Selecione o ano:", reply_markup=reply_markup)

    except mysql.connector.Error as err:
        await query.message.reply_text(f"Erro ao acessar o banco de dados: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# Função para exibir os meses disponíveis
async def selecionar_mes_comissao(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = update.effective_user.id
    _, ano, id_telegram = query.data.split('_')

    try:
        # Conexão com o banco de dados
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)

        # Obtém o celular do barbeiro pelo ID do Telegram
        cursor.execute("SELECT celular FROM barbeiros WHERE id_telegram = %s", (id_telegram,))
        resultado = cursor.fetchone()

        if not resultado:
            await query.message.reply_text("Erro: ID do barbeiro não encontrado.")
            return

        celular_barbeiro = resultado['celular']

        # Consulta para obter os meses disponíveis
        sql = "SELECT DISTINCT MONTH(data) AS mescomissao FROM confirmados WHERE celular_barbeiro = %s AND YEAR(data) = %s"

        cursor.execute(sql, (celular_barbeiro, ano))
        meses = cursor.fetchall()

        # Verifica se há resultados
        if not meses:
            await query.message.reply_text("Nenhum mês encontrado.")
            return

        # Cria os botões para os meses em português
        meses_pt = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        keyboard = []
        for mes in meses:
            nome_mes = meses_pt[mes['mescomissao'] - 1]
            keyboard.append([InlineKeyboardButton(nome_mes, callback_data=f"mescomissao_{mes['mescomissao']}_{ano}_{id_telegram}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Envia a mensagem com os botões dos meses
        await query.message.reply_text("Selecione o mês:", reply_markup=reply_markup)

    except mysql.connector.Error as err:
        await query.message.reply_text(f"Erro ao acessar o banco de dados: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()




# Função para exibir a comissão total com acréscimos e descontos
async def exibir_comissao(update: Update, context: CallbackContext):
    query = update.callback_query
    _, mes, ano, id_telegram = query.data.split('_')

    try:
        # Conexão com o banco de dados
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)

        # Obtém o celular do barbeiro pelo ID do Telegram
        cursor.execute("SELECT celular FROM barbeiros WHERE id_telegram = %s", (id_telegram,))
        resultado = cursor.fetchone()

        if not resultado:
            await query.message.reply_text("Erro: ID do barbeiro não encontrado.")
            return

        celular_barbeiro = resultado['celular']

        # Obtém o último dia do mês
        ultimo_dia = calendar.monthrange(int(ano), int(mes))[1]

        # Consulta para obter as comissões do dia 1 ao 15
        cursor.execute(
            """
            SELECT COALESCE(SUM(comissao), 0) AS total
            FROM confirmados
            WHERE celular_barbeiro = %s AND YEAR(data) = %s AND MONTH(data) = %s AND DAY(data) BETWEEN 1 AND 15
            """,
            (celular_barbeiro, ano, mes)
        )
        total_parte1 = cursor.fetchone()["total"]

        # Consulta para obter as comissões do dia 16 ao último dia do mês
        cursor.execute(
            """
            SELECT COALESCE(SUM(comissao), 0) AS total
            FROM confirmados
            WHERE celular_barbeiro = %s AND YEAR(data) = %s AND MONTH(data) = %s AND DAY(data) BETWEEN 16 AND %s
            """,
            (celular_barbeiro, ano, mes, ultimo_dia)
        )
        total_parte2 = cursor.fetchone()["total"]

        # Consulta para obter acréscimos e descontos do dia 1 ao 15
        cursor.execute(
            """
            SELECT data, tipo, descricao, valor
            FROM taxas
            WHERE celular_barbeiro = %s AND YEAR(data) = %s AND MONTH(data) = %s AND DAY(data) BETWEEN 1 AND 15
            """,
            (celular_barbeiro, ano, mes)
        )
        taxas_parte1 = cursor.fetchall()

        # Consulta para obter acréscimos e descontos do dia 16 ao último dia do mês
        cursor.execute(
            """
            SELECT data, tipo, descricao, valor
            FROM taxas
            WHERE celular_barbeiro = %s AND YEAR(data) = %s AND MONTH(data) = %s AND DAY(data) BETWEEN 16 AND %s
            """,
            (celular_barbeiro, ano, mes, ultimo_dia)
        )
        taxas_parte2 = cursor.fetchall()

        # Separar acréscimos e descontos para os dois períodos
        def formatar_taxas(taxas):
            acrescimos = []
            descontos = []
            total_acrescimos = 0
            total_descontos = 0

            for taxa in taxas:
                data_formatada = datetime.strptime(str(taxa["data"]), "%Y-%m-%d").strftime("%d/%m/%Y")
                if taxa["tipo"] == "acréscimo":
                    acrescimos.append(f"\nData: {data_formatada}\nDescrição: {taxa['descricao']}\nValor: R$ {taxa['valor']:.2f}")
                    total_acrescimos += taxa["valor"]
                elif taxa["tipo"] == "desconto":
                    descontos.append(f"\nData: {data_formatada}\nDescrição: {taxa['descricao']}\nValor: R$ {taxa['valor']:.2f}")
                    total_descontos += taxa["valor"]

            return acrescimos, descontos, total_acrescimos, total_descontos

        acrescimos_parte1, descontos_parte1, total_acrescimos1, total_descontos1 = formatar_taxas(taxas_parte1)
        acrescimos_parte2, descontos_parte2, total_acrescimos2, total_descontos2 = formatar_taxas(taxas_parte2)

        # Cálculo final dos valores a receber
        valor_receber_parte1 = total_parte1 + total_acrescimos1 - total_descontos1
        valor_receber_parte2 = total_parte2 + total_acrescimos2 - total_descontos2
        valor_total_mes = valor_receber_parte1 + valor_receber_parte2

        # Meses em português
        meses_pt = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        nome_mes = meses_pt[int(mes) - 1]

        # Formata a mensagem
        resposta = (
            f"A comissão do barbeiro no mês de {nome_mes} de {ano} é:\n\n"
            f"Valor entre o dia 01 a 15\nR$ {total_parte1:.2f}\n\n"
            f"➕Acréscimos:\n" + ("\n".join(acrescimos_parte1) if acrescimos_parte1 else "Nenhum valor aplicado") + "\n\n"
            f"➖Descontos:\n" + ("\n".join(descontos_parte1) if descontos_parte1 else "Nenhum valor aplicado") + "\n\n"
            f"Valor a receber:\n✅R$ {valor_receber_parte1:.2f}\n\n"
            f"Valor entre o dia 16 a {ultimo_dia}\nR$ {total_parte2:.2f}\n\n"
            f"➕Acréscimos:\n" + ("\n".join(acrescimos_parte2) if acrescimos_parte2 else "Nenhum valor aplicado") + "\n\n"
            f"➖Descontos:\n" + ("\n".join(descontos_parte2) if descontos_parte2 else "Nenhum valor aplicado") + "\n\n"
            f"Valor a receber:\n✅R$ {valor_receber_parte2:.2f}\n\n"
            f"Valor total recebido do mês R$ {valor_total_mes:.2f}"
        )

        # Define os botões "Menu" e "Consultar Novamente"
        keyboard = [
            [InlineKeyboardButton("Consultar Novamente", callback_data="comissao_barbeiro")],
            [InlineKeyboardButton("Menu", callback_data="menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Envia a mensagem para o usuário com os botões
        await query.message.reply_text(
            resposta,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    except mysql.connector.Error as err:
        await query.message.reply_text(f"Erro ao acessar o banco de dados: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()















# Função para exibir anos disponíveis
async def selecionar_ano_faturamento(update: Update, context: CallbackContext):
    query = update.callback_query
    button_name = "Faturamento Mês"  # Nome do botão
    log_usuario(update, button_name)  # Log para registrar quem clicou no botão
    await query.answer()

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Obtém os anos distintos da tabela confirmados
        cursor.execute("SELECT DISTINCT EXTRACT(YEAR FROM data) FROM confirmados ORDER BY 1 DESC")
        anos = [str(row[0]) for row in cursor.fetchall()]

        if not anos:
            # Cria botões "Consultar Novamente" e "Menu"
            keyboard = [
                [InlineKeyboardButton("Consultar Novamente", callback_data="faturamentomes")],
                [InlineKeyboardButton("Menu", callback_data="menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.message.reply_text("Nenhum dado encontrado.", reply_markup=reply_markup)
            return

        # Cria botões para os anos
        keyboard = [[InlineKeyboardButton(ano, callback_data=f"anofaturamento_{ano}")] for ano in anos]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.reply_text("Selecione um ano:", reply_markup=reply_markup)

    except mysql.connector.Error as err:
        await query.message.reply_text(f"Erro ao acessar o banco de dados: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Dicionário para mapear o número do mês para o nome do mês
meses_nome = {
    "1": "Janeiro", "2": "Fevereiro", "3": "Março", "4": "Abril", "5": "Maio", "6": "Junho",
    "7": "Julho", "8": "Agosto", "9": "Setembro", "10": "Outubro", "11": "Novembro", "12": "Dezembro"
}

# Função para exibir meses disponíveis com base no ano selecionado
async def selecionar_mes_faturamento(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    ano_selecionado = query.data.split("_")[1]  # Extrai o ano da callback_data

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Obtém os meses disponíveis no ano selecionado
        cursor.execute(f"SELECT DISTINCT EXTRACT(MONTH FROM data) FROM confirmados WHERE EXTRACT(YEAR FROM data) = {ano_selecionado} ORDER BY 1")
        meses = [str(row[0]) for row in cursor.fetchall()]

        if not meses:
            await query.message.reply_text("Nenhum mês disponível para este ano.")
            return

        # Cria botões para os meses com os nomes em vez dos números
        keyboard = [[InlineKeyboardButton(f"{meses_nome[mes]}", callback_data=f"mesfaturamento_{ano_selecionado}_{mes}")] for mes in meses]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.reply_text(f"Selecione um mês:", reply_markup=reply_markup)

    except mysql.connector.Error as err:
        await query.message.reply_text(f"Erro ao acessar o banco de dados: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Função para calcular e exibir o faturamento líquido do mês selecionado
async def exibir_faturamento(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    _, ano, mes = query.data.split("_")  # Extrai ano e mês da callback_data

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)

        # Calcula o faturamento bruto (soma da coluna 'valor' na tabela confirmados)
        cursor.execute(
            """
            SELECT COALESCE(SUM(valor), 0) AS faturamento_bruto
            FROM confirmados 
            WHERE YEAR(data) = %s AND MONTH(data) = %s
            """,
            (ano, mes)
        )
        faturamento_bruto = cursor.fetchone()["faturamento_bruto"]

        # Calcula o total de comissões (coluna 'comissao' da tabela confirmados)
        cursor.execute(
            """
            SELECT COALESCE(SUM(comissao), 0) AS total_comissao
            FROM confirmados
            WHERE YEAR(data) = %s AND MONTH(data) = %s
            """,
            (ano, mes)
        )
        total_comissao = cursor.fetchone()["total_comissao"]

        # Calcula os acréscimos e descontos na tabela 'taxas' para todos os barbeiros no mês
        cursor.execute(
            """
            SELECT 
                SUM(CASE WHEN tipo = 'acréscimo' THEN valor ELSE 0 END) AS total_acrescimos,
                SUM(CASE WHEN tipo = 'desconto' THEN valor ELSE 0 END) AS total_descontos
            FROM taxas
            WHERE YEAR(data) = %s AND MONTH(data) = %s
            """,
            (ano, mes)
        )
        taxas_resultado = cursor.fetchone()
        total_acrescimos = taxas_resultado["total_acrescimos"] or 0
        total_descontos = taxas_resultado["total_descontos"] or 0

        # Ajusta a comissão com os acréscimos e descontos
        comissao_ajustada = total_comissao + total_acrescimos - total_descontos

        # Calcula o faturamento líquido
        faturamento_liquido = faturamento_bruto - comissao_ajustada

        # Formata o nome do mês
        meses_pt = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ]
        nome_mes = meses_pt[int(mes) - 1]

        # Formata a resposta com os valores
        resposta = (
            f"Faturamento de {nome_mes} de {ano}:\n\n"
            f"Faturamento Bruto: R$ {faturamento_bruto:,.2f}\n"
            f"Total de Comissões: R$ {total_comissao:,.2f}\n"
            f"Acréscimos: R$ {total_acrescimos:,.2f}\n"
            f"Descontos: R$ {total_descontos:,.2f}\n\n"
            f"Faturamento Líquido: R$ {faturamento_liquido:,.2f}"
        )

        # Define os botões "Menu" e "Consultar Novamente"
        keyboard = [
            [InlineKeyboardButton("Consultar Novamente", callback_data="faturamentomes")],
            [InlineKeyboardButton("Menu", callback_data="menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Envia a mensagem para o usuário com os botões
        await query.message.reply_text(
            resposta,
            reply_markup=reply_markup
        )

    except mysql.connector.Error as err:
        await query.message.reply_text(f"Erro ao acessar o banco de dados: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


























async def ajustar_comissao(update: Update, context: CallbackContext):
    query = update.callback_query
    button_name = "Ajustar Comissão"
    log_usuario(update, button_name)

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT celular, nome FROM barbeiros WHERE status = 'ativo'")
        barbeiros = cursor.fetchall()

        if not barbeiros:
            keyboard = [
                [InlineKeyboardButton("Consultar Novamente", callback_data="comissao_barbeiro")],
                [InlineKeyboardButton("Menu", callback_data="menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("Nenhum dado encontrado.", reply_markup=reply_markup)
            return

        keyboard = [[InlineKeyboardButton(barbeiro["nome"], callback_data=f"barbeiro_{barbeiro['celular']}")] for barbeiro in barbeiros]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Selecione um barbeiro:", reply_markup=reply_markup)
    finally:
        cursor.close()
        conn.close()




async def detalhes_barbeiro(update: Update, context: CallbackContext):
    query = update.callback_query
    celular_barbeiro = query.data.split("_")[1]
    
    # Obtém o mês e ano atuais no horário de Brasília
    data_atual = datetime.now(pytz.timezone('America/Sao_Paulo'))
    mes_atual = str(data_atual.month)  # Converte para string para buscar no dicionário
    ano_atual = str(data_atual.year)
    nome_mes_atual = meses_nome[mes_atual]  # Obtém o nome do mês
    
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor(dictionary=True)
    
    # Filtra apenas os dados do mês e ano atuais
    cursor.execute("SELECT data, tipo, descricao, valor FROM taxas WHERE celular_barbeiro = %s AND MONTH(data) = %s AND YEAR(data) = %s", 
                   (celular_barbeiro, mes_atual, ano_atual))
    taxas = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    if not taxas:
        mensagem = f"Nenhum dado encontrado para {nome_mes_atual}."
    else:
        acrescimos = []
        descontos = []
        
        for t in taxas:
            data_formatada = datetime.strptime(str(t['data']), '%Y-%m-%d').strftime('%d/%m/%Y')
            entrada_formatada = f"\nData: {data_formatada}\nDescrição: {t['descricao']}\nValor: R$ {t['valor']}\n"
            
            if t['tipo'].lower() == "acréscimo":
                acrescimos.append(entrada_formatada)
            else:
                descontos.append(entrada_formatada)
        
        mensagem = f"Dados encontrados para {nome_mes_atual}:\n\n"
        if acrescimos:
            mensagem += "➕Acréscimos:\n" + "".join(acrescimos) + "\n"
        if descontos:
            mensagem += "➖Descontos:\n" + "".join(descontos)
    
    keyboard = [
        [InlineKeyboardButton("Adicionar Acréscimo", callback_data=f"adicionar_acrescimo_{celular_barbeiro}")],
        [InlineKeyboardButton("Adicionar Desconto", callback_data=f"adicionar_desconto_{celular_barbeiro}")],
        [InlineKeyboardButton("Menu", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(mensagem, reply_markup=reply_markup)







async def adicionar_acrescimo(update: Update, context: CallbackContext):
    query = update.callback_query
    celular_barbeiro = query.data.split("_")[2]
    context.user_data["celular_barbeiro"] = celular_barbeiro
    context.user_data["aguardando_input"] = "DESCRICAO_ACRESCIMO"  # Define o estado correto

    await query.message.reply_text("Qual descrição do acréscimo?")
    return

async def receber_descricao_acrescimo(update: Update, context: CallbackContext):
    descricao = update.message.text
    if re.search(r'\d', descricao):
        await update.message.reply_text("A descrição não pode conter números. Digite novamente:")
        return  # Apenas retorna, sem mudar o estado
    
    context.user_data["descricao"] = descricao
    context.user_data["aguardando_input"] = "VALOR_ACRESCIMO"  # Atualiza o estado corretamente
    
    await update.message.reply_text("Qual valor do acréscimo?")

async def receber_valor_acrescimo(update: Update, context: CallbackContext):
    valor = update.message.text.replace(",", ".")  # Substitui vírgula por ponto

    if not re.match(r'^[0-9]+(\.[0-9]{1,2})?$', valor):
        await update.message.reply_text("O valor deve ser numérico. Digite novamente:")
        return  # Apenas retorna, sem mudar o estado

    celular_barbeiro = context.user_data["celular_barbeiro"]
    descricao = context.user_data["descricao"]
    data_atual = datetime.now().strftime('%Y-%m-%d')

    # Insere os dados no banco
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO taxas (data, celular_barbeiro, tipo, descricao, valor) VALUES (%s, %s, %s, %s, %s)",
                   (data_atual, celular_barbeiro, "Acréscimo", descricao, valor))
    conn.commit()
    cursor.close()
    conn.close()

    # Limpa o contexto
    context.user_data.pop("aguardando_input", None)
    context.user_data.pop("descricao", None)  # Removemos a descrição para evitar dados antigos
    context.user_data.pop("celular_barbeiro", None)

    # Define os botões "Adicionar Novamente" e "Menu"
    keyboard = [
        [InlineKeyboardButton("Adicionar Novamente", callback_data="ajustar_comissao")],
        [InlineKeyboardButton("Menu", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Acréscimo registrado com sucesso!", reply_markup=reply_markup)



    


async def adicionar_desconto(update: Update, context: CallbackContext):
    query = update.callback_query
    celular_barbeiro = query.data.split("_")[2]
    context.user_data["celular_barbeiro"] = celular_barbeiro
    context.user_data["aguardando_input"] = "DESCRICAO_DESCONTO"  # Define o estado correto

    await query.message.reply_text("Qual descrição do desconto?")
    return

async def receber_descricao_desconto(update: Update, context: CallbackContext):
    descricao = update.message.text
    if re.search(r'\d', descricao):
        await update.message.reply_text("A descrição não pode conter números. Digite novamente:")
        return
    
    context.user_data["descricao"] = descricao
    context.user_data["aguardando_input"] = "VALOR_DESCONTO"  # Define corretamente o próximo estado
    
    await update.message.reply_text("Qual valor do desconto?")


async def receber_valor_desconto(update: Update, context: CallbackContext):
    valor = update.message.text.replace(",", ".")

    if not re.match(r'^[0-9]+(\.[0-9]{1,2})?$', valor):
        await update.message.reply_text("O valor deve ser numérico. Digite novamente:")
        return

    celular_barbeiro = context.user_data["celular_barbeiro"]
    descricao = context.user_data["descricao"]
    data_atual = datetime.now().strftime('%Y-%m-%d')

    # Insere os dados no banco
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO taxas (data, celular_barbeiro, tipo, descricao, valor) VALUES (%s, %s, %s, %s, %s)",
                   (data_atual, celular_barbeiro, "Desconto", descricao, valor))
    conn.commit()
    cursor.close()
    conn.close()

    # Limpa o contexto
    context.user_data.pop("aguardando_input", None)
    context.user_data.pop("descricao", None)
    context.user_data.pop("celular_barbeiro", None)

    # Define os botões "Adicionar Novamente" e "Menu"
    keyboard = [
        [InlineKeyboardButton("Adicionar Novamente", callback_data="ajustar_comissao")],
        [InlineKeyboardButton("Menu", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Desconto registrado com sucesso!", reply_markup=reply_markup)





















# Função para tratar o callback dos botões
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == "lista_barbeiro":
        # Chama a função de listar barbeiros
        await lista_barbeiro(update, context)
    elif query.data == "menu":
        # Retorna ao menu principal
        await menu(update, context)
    elif query.data == "cortes_barbeiro":
        # Chama a função de listar barbeiros para cortes
        await cortes_barbeiro(update, context)


    elif query.data.startswith("barbeirocortes_"):
        # Chama a função de selecionar ano
        await selecionar_ano_cortes(update, context)
    elif query.data.startswith("anocorte_"):
        # Chama a função de selecionar mês
        await selecionar_mes_cortes(update, context)
    elif query.data.startswith("mescortes_"):
        # Chama a função de exibir cortes
        await exibir_cortes(update, context)
    elif query.data == "comissao_barbeiro":
        # Chama a função de listar barbeiros para cortes
        await comissao_barbeiro(update, context)


    elif query.data.startswith("barbeirocomissao_"):
        # Chama a função de selecionar ano para comissão
        await selecionar_ano_comissao(update, context)
    elif query.data.startswith("anocomissao_"):
        # Chama a função de selecionar mês para comissão
        await selecionar_mes_comissao(update, context)
    elif query.data.startswith("mescomissao_"):
        # Chama a função correta de exibição de comissão
        await exibir_comissao(update, context)




    elif query.data == "faturamentomes":
        # Chama a função para selecionar tipo de faturamento
        await selecionar_ano_faturamento(update, context)

    elif query.data.startswith("anofaturamento_"):
        # Chama a função de selecionar mês
        await selecionar_mes_faturamento(update, context)
    elif query.data.startswith("mesfaturamento_"):
        # Chama a função de exibir faturamento
        await exibir_faturamento(update, context)




    elif query.data.startswith("ajustar_comissao"):
        # Chama a função para exibir os barbeiros
        await ajustar_comissao(update, context)

    elif query.data.startswith("barbeiro_"):
        # Chama a função para exibir detalhes do barbeiro selecionado
        await detalhes_barbeiro(update, context)

    elif query.data.startswith("adicionar_acrescimo_"):
        # Chama a função para adicionar acréscimo
        await adicionar_acrescimo(update, context)

    elif query.data.startswith("adicionar_desconto_"):
        # Chama a função para adicionar desconto
        await adicionar_desconto(update, context)















# Função para redirecionar o usuário com base no contexto ou comando
async def entrada_usuario(update: Update, context: CallbackContext):
    # Verifica se há um contexto específico em andamento
    if context.user_data.get("aguardando_input") == "lista_barbeiro":
        await lista_barbeiro(update, context)
        return

    elif context.user_data.get("aguardando_input") == "DESCRICAO_ACRESCIMO":
        await receber_descricao_acrescimo(update, context)
        return

    elif context.user_data.get("aguardando_input") == "VALOR_ACRESCIMO":
        await receber_valor_acrescimo(update, context)
        return

    elif context.user_data.get("aguardando_input") == "DESCRICAO_DESCONTO":
        await receber_descricao_desconto(update, context)
        return

    elif context.user_data.get("aguardando_input") == "VALOR_DESCONTO":
        await receber_valor_desconto(update, context)
        return

    # Se a mensagem não for um comando reconhecido, redireciona para o menu
    if update.message.text not in ['/start', '/menu']:
        await menu(update, context)









# Inicializar o bot
def run_bot():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Handlers de comandos
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT, entrada_usuario))
    application.add_handler(CallbackQueryHandler(button_handler))  # Para lidar com botões

    # Inicia o bot
    application.run_polling()

# Função para rodar o cron job
def run_cron_job():
    ajustar_horario_execucao()

    while True:
        schedule.run_pending()
        time.sleep(1)

# Função principal para rodar o Flask
def main():
    # Rodar o Flask em uma thread separada sem SSL
    threading.Thread(
        target=app.run,
        kwargs={
            "host": "0.0.0.0",  # Permite acesso externo
            "port": 8080,        # Porta padrão
            "debug": False,       # Ativa o modo debug (desativar em produção)
            "use_reloader": False,  # Evita múltiplos processos na thread
        },
    ).start()

    # Rodar o monitoramento de mensagens em uma thread separada
    threading.Thread(target=enviar_mensagem_barbeiro).start()

    # Rodar o monitoramento de confirmados em uma thread separada
    threading.Thread(target=enviar_mensagem_confirmados).start()

    # Rodar o cron job em uma thread separada
    threading.Thread(target=run_cron_job).start()

    # Rodar o bot no processo principal
    run_bot()

# Início do programa
if __name__ == "__main__":
    main()