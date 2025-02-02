import threading
from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from datetime import datetime, date 
import time as time_module 


# Módulos padrão do Python
import logging
import datetime  # Importa o módulo completo para evitar conflitos
from datetime import datetime
import requests


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


app = Flask(__name__)
app.secret_key = "{k>9IysL&3DQ?cl8rcP4"



config = {
    'user': 'root',
    'password': 'mLlXOVHTXFYdfYQinXuSLPhQxPtkamDF',  # Senha do Railway
    'host': 'viaduct.proxy.rlwy.net',  # Host do Railway
    'port': 15447,  # Porta fornecida pelo Railway
    'database': 'railway'  # Nome do banco de dados no Railway
}


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

                # Obtendo a data e o horário atuais
                now = datetime.now()
                current_date = now.strftime('%Y-%m-%d')  # Formato: '2025-01-20'
                current_time = now.strftime('%H:%M:%S')  # Formato: '02:43:25'

                # Obtendo as informações do horário reservado
                horario_query = """
                SELECT h.id, h.celular_barbeiro, b.nome, DATE_FORMAT(h.data, '%d/%m/%Y') AS data, TIME_FORMAT(h.horario, '%H:%i') AS horario, p.corte, p.valor
                FROM horarios h
                INNER JOIN barbeiros b ON b.celular = h.celular_barbeiro
                INNER join precos p on p.id = h.corte_id 
                WHERE h.celular_cliente = %s AND h.status = 'reservado'
                AND (h.data > %s OR (h.data = %s AND h.horario > %s))
                ORDER BY h.id DESC LIMIT 1
                """
                cursor.execute(horario_query, (celular, current_date, current_date, current_time))
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
                flash("celular não cadastrado. Por favor, cadastre-se abaixo.", "info")
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

        return redirect(url_for('login'))

    return render_template('cadastro.html', celular=celular)





# Página de Bem-vindo
@app.route('/bemvindo')
def bemvindo():
    celular_cliente = request.args.get('celular_cliente')
    nome_cliente = request.args.get('nome_cliente')

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Obtendo a data e o horário atuais
        now = datetime.now()
        current_date = now.strftime('%Y-%m-%d')  # Formato: '2025-01-20'
        current_time = now.strftime('%H:%M:%S')  # Formato: '02:43:25'

        # Obtendo as informações do horário reservado
        horario_query = """
        SELECT h.id, h.celular_barbeiro, b.nome, DATE_FORMAT(h.data, '%d/%m/%Y') AS data, TIME_FORMAT(h.horario, '%H:%i') AS horario, p.corte, p.valor
        FROM horarios h
        INNER JOIN barbeiros b ON b.celular = h.celular_barbeiro
        INNER join precos p on p.id = h.corte_id 
        WHERE h.celular_cliente = %s AND h.status = 'reservado'
          AND (h.data > %s OR (h.data = %s AND h.horario > %s))
        ORDER BY h.id DESC LIMIT 1
        """
        cursor.execute(horario_query, (celular_cliente, current_date, current_date, current_time))
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









# Lista de barbeiros
@app.route('/cortes')
def cortes():
    celular_cliente = request.args.get('celular_cliente')
    nome_cliente = request.args.get('nome_cliente')

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        query = "select id,corte,valor from precos"
        cursor.execute(query)
        cortes = cursor.fetchall()
        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        flash(f"Erro ao buscar cortes: {err}", "danger")
        cortes = []

    return render_template('cortes.html', cortes=cortes, celular_cliente=celular_cliente, nome_cliente=nome_cliente)






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

        # Obtendo a data atual
        current_date = datetime.now().strftime('%Y-%m-%d')  # Formato: '2025-01-20'

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

        # Obter o horário atual no formato HH:MM:SS
        hora_atual = datetime.now().time()
        # Obter a data atual
        data_atual = date.today()

        # Ajustar a consulta SQL com base na data selecionada
        if data_obj == data_atual:
            # Se a data selecionada for o dia atual, filtrar horários >= hora atual
            query = """
                SELECT horario, status
                FROM horarios
                WHERE celular_barbeiro = %s 
                  AND data = %s 
                  AND horario >= %s
                  AND status = 'disponível'
                ORDER BY horario
            """
            cursor.execute(query, (celular_barbeiro, data, hora_atual))
        else:
            # Se a data selecionada for futura, não filtrar pelo horário
            query = """
                SELECT horario, status
                FROM horarios
                WHERE celular_barbeiro = %s 
                  AND data = %s 
                  AND status = 'disponível'
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



# Tela de confirmação de reserva de horário
@app.route('/reserva_confirmada')
def reserva_confirmada():
    nome_barbeiro = request.args.get('nome_barbeiro')
    horario = request.args.get('horario')
    data = request.args.get('data')
    corte = request.args.get('corte')
    valor = request.args.get('valor')

    # Formatar o horário para exibir sem os segundos
    horario_formatado = ":".join(horario.split(":")[:2])

    return render_template(
        'reserva_confirmada.html',
        nome_barbeiro=nome_barbeiro,
        horario=horario_formatado,
        data=data,
        corte=corte,
        valor=valor
    )













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

        # Obtendo a data atual
        current_date = datetime.now().strftime('%Y-%m-%d')
        formatted_date = datetime.now().strftime('%d/%m/%Y')

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

        # Obtendo a data atual
        current_date = datetime.now().strftime('%Y-%m-%d')
        formatted_date = datetime.now().strftime('%d/%m/%Y')

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






# Função para confirmar o corte
@app.route('/confirmar_corte/<int:horario_id>', methods=['POST'])
def confirmar_corte(horario_id):
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        # Obtendo a data atual
        current_date = datetime.now().strftime('%Y-%m-%d')

        # Inserir dados na tabela confirmados
        insert_query = """
        INSERT INTO confirmados (data, horario, celular_barbeiro, celular_cliente, corte, valor, porcentagem, comissao)
        SELECT 
            h.data,
            h.horario, 
            h.celular_barbeiro, 
            h.celular_cliente,
            p.corte, 
            p.valor, 
            b.porcentagem,
            (b.porcentagem / 100) * p.valor AS comissao
        FROM horarios h
        INNER JOIN barbeiros b ON b.celular = h.celular_barbeiro
        INNER JOIN precos p ON p.id = h.corte_id
        WHERE h.id = %s AND h.data = %s AND h.status = 'reservado'
        """
        cursor.execute(insert_query, (horario_id, current_date))

        # Recuperar as informações inseridas na tabela confirmados
        select_query = """
        SELECT DATE_FORMAT(cf.data, '%d/%m/%Y') AS data, TIME_FORMAT(cf.horario, '%H:%i') AS horario, 
               b.nome AS barbeiro, c.nome AS cliente, cf.corte, cf.valor AS valor_do_corte, cf.comissao AS comissao_do_barbeiro
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
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Corrigido para datetime.now()
    comando = update.message.text if update.message else "Botão clicado"
    if button_name:
        comando = f"Botão {button_name} clicado"
    logger.info(f"Informação {comando} recebido em {data_hora} ID={user_id}, Usuário={user_name}\n")



# Lista de IDs de autorização total
AUTHORIZED_USER_IDS = [637172689]  # IDs com acesso total

# Lista de IDs de autorização limitada (será preenchida dinamicamente)
LIMITED_ACCESS_USER_IDS = []

# IDs descritos
# ID=637172689 = Márcio Garcia
# ID=6415636681 = Márcio Corporativo


# Função para carregar os IDs dos barbeiros
def carregar_ids_barbeiros():
    try:
        # Conexão com o banco de dados
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)

        # Consulta para obter os IDs dos barbeiros
        cursor.execute("SELECT id_telegram FROM barbeiros")
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
            f"Olá, {user_name}!👋\nVocê não está autorizado a acessar o Bot Luka Barbearia. Por favor, entre em contato com Márcio Garcia para liberação."
        )
        return

    # Define o menu com base na autorização
    if user_id in LIMITED_ACCESS_USER_IDS:
        # Menu para usuários com acesso limitado
        keyboard = [
            [InlineKeyboardButton("Agendar Horário", url="http://pcmarcio.ddns.net")],
            [InlineKeyboardButton("Confirmar Corte", url="http://pcmarcio.ddns.net/selecionar_barbeiro")],
            [InlineKeyboardButton("Cortes por Barbeiro", callback_data="cortes_barbeiro")],
            [InlineKeyboardButton("Comissão por Barbeiro", callback_data="comissao_barbeiro")],
        ]
        welcome_message = f"Olá, {user_name}! 👋\nBem-vindo ao *Bot Luka Barbearia*! 💪\n\nAqui estão as opções disponíveis no menu:"
    else:
        # Menu para usuários com acesso total
        keyboard = [
            [InlineKeyboardButton("Agendar Horário", url="http://pcmarcio.ddns.net")],
            [InlineKeyboardButton("Cadastrar Barbeiro", url="http://pcmarcio.ddns.net/consultar_barbeiro")],
            [InlineKeyboardButton("Confirmar Corte", url="http://pcmarcio.ddns.net/selecionar_barbeiro")],
            [InlineKeyboardButton("Lista Barbeiros", callback_data="lista_barbeiro")],
            [InlineKeyboardButton("Cortes por Barbeiro", callback_data="cortes_barbeiro")],
            [InlineKeyboardButton("Comissão por Barbeiro", callback_data="comissao_barbeiro")],
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
    user_id = str(update.effective_user.id)  # Converte o user_id para string
    user_name = update.effective_user.full_name  # Obtém o nome completo do usuário

    # Verifica se o usuário está autorizado
    if user_id not in map(str, AUTHORIZED_USER_IDS) and user_id not in LIMITED_ACCESS_USER_IDS:
        # Loga a tentativa de acesso de usuário não autorizado
        print(f"Tentativa de acesso de usuário não autorizado ao menu: {user_name} (ID: {user_id})")

        # Envia mensagem informando que o usuário não está autorizado
        await update.message.reply_text(
            f"Olá, {user_name}!👋\nVocê não está autorizado a acessar o Bot Luka Barbearia. Por favor, entre em contato com Márcio Garcia para liberação."
        )
        return

    # Define o menu com base na autorização
    if user_id in LIMITED_ACCESS_USER_IDS:
        # Menu para usuários com acesso limitado
        keyboard = [
            [InlineKeyboardButton("Agendar Horário", url="http://pcmarcio.ddns.net")],
            [InlineKeyboardButton("Cadastrar Barbeiro", url="http://pcmarcio.ddns.net/consultar_barbeiro")],
            [InlineKeyboardButton("Cortes por Barbeiro", callback_data="cortes_barbeiro")],
            [InlineKeyboardButton("Comissão por Barbeiro", callback_data="comissao_barbeiro")],
        ]
        message_text = "Escolha uma opção:"
    else:
        # Menu para usuários com acesso total
        keyboard = [
            [InlineKeyboardButton("Agendar Horário", url="http://pcmarcio.ddns.net")],
            [InlineKeyboardButton("Cadastrar Barbeiro", url="http://pcmarcio.ddns.net/consultar_barbeiro")],
            [InlineKeyboardButton("Confirmar Corte", url="http://pcmarcio.ddns.net/selecionar_barbeiro")],
            [InlineKeyboardButton("Lista Barbeiros", callback_data="lista_barbeiro")],
            [InlineKeyboardButton("Cortes por Barbeiro", callback_data="cortes_barbeiro")],
            [InlineKeyboardButton("Comissão por Barbeiro", callback_data="comissao_barbeiro")],
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
    """Monitora a tabela mensagem e envia notificações para mensagens pendentes."""
    while True:
        try:
            # Conectar ao banco de dados
            conn = mysql.connector.connect(**config)
            cursor = conn.cursor(dictionary=True)
            
            # Buscar mensagens com status pendente
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
                    # Atualizar status para enviado
                    cursor.execute("UPDATE mensagem SET status = 'enviado' WHERE id = %s", (msg['id'],))
                    conn.commit()
            
            cursor.close()
            conn.close()
        
        except Exception as e:
            print(f"Erro: {e}")
        
        # Espera 5 segundos antes de rodar novamente
        time_module.sleep(5)



def enviar_mensagem_confirmados():
    """Verifica a tabela confirmados e envia notificações para mensagens pendentes."""
    while True:
        try:
            # Conectar ao banco de dados
            conn = mysql.connector.connect(**config)
            cursor = conn.cursor(dictionary=True)
            
            # Buscar mensagens com status pendente
            cursor.execute("""
                SELECT c.id, c.data, c.horario, b.nome AS nome_barbeiro, cl.nome AS nome_cliente, c.corte, c.valor, c.comissao 
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
*✂️ Corte Realizado! ✂️*\n
E aí, Lucas, o {conf['nome_barbeiro']} mandou bem demais! 🎉\n
📅 *Data:* {data_formatada}
⏰ *Horário:* {horario_formatado}
👤*Cliente:* {conf['nome_cliente']}
✂️ *Corte:* {conf['corte']}
💵 *Valor:* {conf['valor']}
💰 *Comissão:* {conf['comissao']}\n
O cliente saiu satisfeito e o caixa agradece!💸
Bora continuar arrasando!+💪🔥
                """
                
                if enviar_mensagem(637172689, mensagem_texto):
                    print(f"Mensagem enviada com sucesso para o ID 637172689")
                    # Atualizar status para enviado
                    cursor.execute("UPDATE confirmados SET status = 'enviado' WHERE id = %s", (conf['id'],))
                    conn.commit()
            
            cursor.close()
            conn.close()
        
        except Exception as e:
            print(f"Erro: {e}")
        
        # Espera 5 segundos antes de rodar novamente
        time_module.sleep(5)







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
            SELECT c.data, c.horario, b.nome AS nome_barbeiro, cl.nome AS nome_cliente, c.corte,c.valor, c.comissao 
            FROM confirmados c
            INNER JOIN barbeiros b ON b.celular = c.celular_barbeiro 
            INNER JOIN clientes cl ON cl.celular = c.celular_cliente 
            WHERE b.id_telegram = %s AND YEAR(c.data) = %s AND MONTH(c.data) = %s
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
            mensagens.append(f"*Data:* {data_formatada}\n*Horário:* {horario_formatado}\n*Cliente:* {corte['nome_cliente']}\n*Corte:* {corte['corte']}\n*valor:* R$ {corte['valor']}\n*Comissão:* R$ {corte['comissao']}\n\n")

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




# Função para exibir a comissão total
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

        # Consulta para obter as comissões
        sql = """
            SELECT comissao 
            FROM confirmados 
            WHERE celular_barbeiro = %s AND YEAR(data) = %s AND MONTH(data) = %s
        """

        cursor.execute(sql, (celular_barbeiro, ano, mes))
        comissoes = cursor.fetchall()

        # Verifica se há resultados
        if not comissoes:
            await query.message.reply_text("Nenhuma comissão encontrada.")
            return

        # Calcula a soma das comissões
        total_comissao = sum(comissao["comissao"] for comissao in comissoes)

        # Meses em português
        meses_pt = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        nome_mes = meses_pt[int(mes) - 1]

        # Formata a mensagem para o usuário
        resposta = f"A comissão total do barbeiro no mês de {nome_mes} de {ano} é:\n\nR$ {total_comissao:.2f}"

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








# Função para exibir os botões "Líquido" e "Bruto"
async def selecionar_tipo_faturamento(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    # Cria os botões "Líquido" e "Bruto"
    keyboard = [
        [InlineKeyboardButton("Líquido", callback_data="faturamentoliquido")],
        [InlineKeyboardButton("Bruto", callback_data="faturamentobruto")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Envia a mensagem com os botões
    await query.message.reply_text("Selecione o tipo de faturamento:", reply_markup=reply_markup)












# Função para exibir anos disponíveis
async def selecionar_ano_faturamento_liquido(update: Update, context: CallbackContext):
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
        keyboard = [[InlineKeyboardButton(ano, callback_data=f"anofaturamentoliquido_{ano}")] for ano in anos]
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
async def selecionar_mes_faturamento_liquido(update: Update, context: CallbackContext):
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
        keyboard = [[InlineKeyboardButton(f"{meses_nome[mes]}", callback_data=f"mesfaturamentoliquido_{ano_selecionado}_{mes}")] for mes in meses]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.reply_text(f"Selecione um mês:", reply_markup=reply_markup)

    except mysql.connector.Error as err:
        await query.message.reply_text(f"Erro ao acessar o banco de dados: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Função para calcular e exibir o faturamento do mês selecionado
async def exibir_faturamento_liquido(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    _, ano, mes = query.data.split("_")  # Extrai ano e mês da callback_data

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Calcula o faturamento do período selecionado
        cursor.execute(f"""
            SELECT SUM(valor-comissao) as faturamento_liquido
            FROM confirmados 
            WHERE EXTRACT(YEAR FROM data) = {ano} 
            AND EXTRACT(MONTH FROM data) = {mes}
        """)
        faturamento = cursor.fetchone()[0] or 0

        # Formata a resposta com o faturamento
        resposta = f"O faturamento de {meses_nome[mes]} de {ano} é:\n\nR$ {faturamento:,.2f}"

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





















# Função para exibir anos disponíveis
async def selecionar_ano_faturamento_bruto(update: Update, context: CallbackContext):
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
        keyboard = [[InlineKeyboardButton(ano, callback_data=f"anofaturamentobruto_{ano}")] for ano in anos]
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
async def selecionar_mes_faturamento_bruto(update: Update, context: CallbackContext):
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
        keyboard = [[InlineKeyboardButton(f"{meses_nome[mes]}", callback_data=f"mesfaturamentobruto_{ano_selecionado}_{mes}")] for mes in meses]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.reply_text(f"Selecione um mês:", reply_markup=reply_markup)

    except mysql.connector.Error as err:
        await query.message.reply_text(f"Erro ao acessar o banco de dados: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Função para calcular e exibir o faturamento do mês selecionado
async def exibir_faturamento_bruto(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    _, ano, mes = query.data.split("_")  # Extrai ano e mês da callback_data

    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Calcula o faturamento do período selecionado
        cursor.execute(f"""
            SELECT SUM(valor) as faturamento_bruto
            FROM confirmados 
            WHERE EXTRACT(YEAR FROM data) = {ano} 
            AND EXTRACT(MONTH FROM data) = {mes}
        """)
        faturamento = cursor.fetchone()[0] or 0

        # Formata a resposta com o faturamento
        resposta = f"O faturamento de {meses_nome[mes]} de {ano} é:\n\nR$ {faturamento:,.2f}"

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
        await selecionar_tipo_faturamento(update, context)

    elif query.data == "faturamentoliquido":
        # Chama a função de selecionar ano para faturamento líquido
        await selecionar_ano_faturamento_liquido(update, context)


    elif query.data.startswith("anofaturamentoliquido_"):
        # Chama a função de selecionar mês
        await selecionar_mes_faturamento_liquido(update, context)
    elif query.data.startswith("mesfaturamentoliquido_"):
        # Chama a função de exibir faturamento
        await exibir_faturamento_liquido(update, context)





    elif query.data == "faturamentobruto":
        # Chama a função de selecionar ano para faturamento bruto
        await selecionar_ano_faturamento_bruto(update, context)    


    elif query.data.startswith("anofaturamentobruto_"):
        # Chama a função de selecionar mês
        await selecionar_mes_faturamento_bruto(update, context)
    elif query.data.startswith("mesfaturamentobruto_"):
        # Chama a função de exibir faturamento
        await exibir_faturamento_bruto(update, context)


















# Função para redirecionar o usuário com base no contexto ou comando
async def entrada_usuario(update: Update, context: CallbackContext):
    # Verifica se há um contexto específico em andamento
    if context.user_data.get("aguardando_input") == "lista_barbeiro":
        await lista_barbeiro(update, context)
        return  # Sai da função após tratar o contexto específico

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


# Função principal para rodar o Flask
def main():
    # Rodar o Flask em uma thread separada sem SSL
    threading.Thread(
        target=app.run,
        kwargs={
            "host": "0.0.0.0",  # Permite acesso externo
            "port": 5000,        # Porta padrão
            "debug": True,       # Ativa o modo debug (desativar em produção)
            "use_reloader": False,  # Evita múltiplos processos na thread
        },
    ).start()

    # Rodar o monitoramento de mensagens em uma thread separada
    threading.Thread(target=enviar_mensagem_barbeiro).start()

    # Rodar o monitoramento de confirmados em uma thread separada
    threading.Thread(target=enviar_mensagem_confirmados).start()

    # Rodar o bot no processo principal
    run_bot()

# Início do programa
if __name__ == "__main__":
    main()








# # Função principal para rodar o Flask
# def main():
#      # Rodar o Flask em uma thread separada com SSL
#      threading.Thread(
#          target=app.run,
#          kwargs={
#              "host": "0.0.0.0",
#              "port": 5000,
#              "ssl_context": ("certificate.crt", "private.key"),
#              "debug": True,
#              "use_reloader": False,  # Evita múltiplos processos na thread
#          },
#      ).start()

#      # Rodar o bot no processo principal
#      run_bot()

#  # Início do programa
# if __name__ == "__main__":
#      main()