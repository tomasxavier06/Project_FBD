from flask import Flask, redirect, render_template, request, jsonify, session, flash
import pyodbc
import hashlib

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui_123'  # Necessário para sessões

# Configuração da base de dados
DB_CONFIG = {
    'server': 'tcp:mednat.ieeta.pt\\SQLSERVER,8101',
    'database': 'p1g7',
    'username': 'p1g7',
    'password': '-375018182@BD'
}

# Função para obter conexão com a BD (SQL Server Authentication)
def get_db_connection():
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={DB_CONFIG['server']};DATABASE={DB_CONFIG['database']};UID={DB_CONFIG['username']};PWD={DB_CONFIG['password']}"
    return pyodbc.connect(conn_str)

# Função geral para gerar IDs únicos para qualquer tabela
def generate_id(table_name, id_column):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"SELECT ISNULL(MAX({id_column}), 0) + 1 FROM {table_name}"
    cursor.execute(query) 
    new_id = cursor.fetchone()[0]
    conn.close()
    return new_id

@app.route('/')
def homepage():
    return render_template('homepage.html')

@app.route('/pilots')
def pilots():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        pesquisa = request.args.get('nome_procurado')
        coluna = request.args.get('coluna', 'nome')
        ordem = request.args.get('ordem', 'asc')

        colunas_validas = ['numero_licenca', 'nome', 'data_nascimento', 'nacionalidade','nome_equipa', 'numero_eventos']

        if coluna not in colunas_validas:
            coluna = 'nome'

        if ordem.lower() not in ['asc', 'desc']:
            ordem = 'asc'

        query = """ SELECT P.numero_licenca, P.nome, P.data_nascimento, P.nacionalidade, E.nome AS nome_equipa, P.numero_eventos, P.foto_piloto
                    FROM Piloto P
                    LEFT JOIN Equipa E ON P.id_equipa = E.id_equipa """
        parametros = []

        if pesquisa:
            query += "WHERE (P.nome LIKE ? OR E.nome LIKE ? OR P.nacionalidade LIKE ?)"
            parametros.append(f"%{pesquisa}%")
            parametros.append(f"%{pesquisa}%")
            parametros.append(f"%{pesquisa}%")

                    
        query += f" ORDER BY {coluna} {ordem}"
        
        cursor.execute(query, tuple(parametros))

        pilotos = cursor.fetchall()
        conn.close()
        return render_template('pilots.html', pilotos=pilotos, ordem_atual = ordem, coluna_ativa = coluna, pesquisa_feita = pesquisa )
    except Exception as e:
        print(f"erro real: {e}")
        return "<h3>Não foi possível carregar os pilotos. Tente novamente</h3>"

@app.route('/teams')
def teams():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        pesquisa = request.args.get('nome_procurado')
        coluna = request.args.get('coluna', 'nome')
        ordem = request.args.get('ordem', 'asc')

        colunas_validas = ['id_equipa', 'nome', 'pais', 'ID_utilizador_diretor_de_equipa']

        if coluna not in colunas_validas:
            coluna = 'nome'

        if ordem.lower() not in ['asc', 'desc']:
            ordem = 'asc'

        query = " SELECT * FROM Equipa "
        parametros = []

        if pesquisa:
            query += "WHERE (nome LIKE ? OR pais LIKE ?)"
            parametros.append(f"%{pesquisa}%")
            parametros.append(f"%{pesquisa}%")

        query += f" ORDER BY {coluna} {ordem}"
        
        cursor.execute(query, tuple(parametros))

        equipas_lista = cursor.fetchall()
        conn.close()
        return render_template('teams.html', equipas = equipas_lista, ordem_atual = ordem, coluna_ativa = coluna, pesquisa_feita = pesquisa )
    except Exception as e:
        print(f"erro real: {e}")
        return "<h3>Não foi possível carregar as equipas. Tente novamente</h3>"
    
@app.route('/team/<int:id>')
def team_details(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT nome, pais FROM Equipa WHERE id_equipa = ?", (id,))
        equipa = cursor.fetchone()

        if not equipa:
            conn.close()
            return "<h3>Equipa não encontrada.</h3>", 404

        
        cursor.execute("""
            SELECT numero_licenca, nome, data_nascimento, nacionalidade, foto_piloto 
            FROM Piloto WHERE id_equipa = ?
        """, (id,))
        pilotos = cursor.fetchall()


        cursor.execute("""
            SELECT VIN, marca, modelo, categoria 
            FROM Carro WHERE id_equipa = ?
        """, (id,))
        carros = cursor.fetchall()

        conn.close()
        return render_template('team_details.html', equipa=equipa, pilotos=pilotos, carros=carros)
    except Exception as e:
        print(f"Erro ao carregar detalhes da equipa: {e}")
        return "<h3>Erro ao carregar detalhes.</h3>"

# Define a rota para a página de eventos
@app.route('/events')
def events():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        pesquisa = request.args.get('nome_procurado')
        coluna = request.args.get('coluna', 'data_inicio')
        ordem = request.args.get('ordem', 'asc')

        colunas_validas = ['id_evento', 'nome', 'tipo', 'data_inicio', 'data_fim', 'status']
        
        if coluna not in colunas_validas:
            coluna = 'data_inicio'
        if ordem.lower() not in ['asc', 'desc']:
            ordem = 'asc'

        query = "SELECT id_evento, nome, tipo, data_inicio, data_fim, status FROM Evento"
        parametros = []

        if pesquisa:
            query += " WHERE (nome LIKE ? OR tipo LIKE ? OR status LIKE ?)"
            parametros.extend([f"%{pesquisa}%"] * 3)
                    
        query += f" ORDER BY {coluna} {ordem}"
        
        cursor.execute(query, tuple(parametros))
        eventos = cursor.fetchall()
        conn.close()
        
        return render_template('events.html', 
                               eventos=eventos, 
                               ordem_atual=ordem, 
                               coluna_ativa=coluna, 
                               pesquisa_feita=pesquisa)
    except Exception as e:
        print(f"Erro real em eventos: {e}")
        return f"<h3>Erro ao carregar eventos: {e}</h3>"

# Define a rota para a página de recordes
@app.route('/records')
def records():
    # Retorna o template records.html
    return render_template('records.html')

@app.route('/welcomeDC')
def welcomeDC():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Precisa fazer login para aceder a esta página!', 'redirect': '/login'}), 401
    conn=get_db_connection()
    cursor=conn.cursor()
    cursor.execute('SELECT * FROM Diretor_de_Corrida WHERE id_utilizador=?',(session['id'],))
    if cursor.fetchone() is None:
        conn.close()
        return redirect('/logout')
    conn.close()
    return render_template('WelcomeDC.html', username=session.get('username', 'Diretor'))

# Routes for Diretor de Corrida - Event Management
@app.route('/criar_evento', methods=['GET', 'POST'])
def criar_evento():
    if 'loggedin' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify user is Diretor de Corrida
    cursor.execute('SELECT * FROM Diretor_de_Corrida WHERE id_utilizador=?', (session['id'],))
    if cursor.fetchone() is None:
        conn.close()
        return redirect('/logout')
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            cursor.execute(
                "INSERT INTO Evento (nome, tipo, data_inicio, data_fim, status, ID_utilizador_gestor_de_corrida) VALUES (?, ?, ?, ?, ?, ?)",
                (data['nome'], data['tipo'], data['data_inicio'], data['data_fim'], 'Por Iniciar', session['id'])
            )
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Evento criado com sucesso!', 'redirect': '/gerir_eventos'})
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 400
    
    conn.close()
    return render_template('criar_evento.html')

@app.route('/gerir_eventos')
def gerir_eventos():
    if 'loggedin' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify user is Diretor de Corrida
    cursor.execute('SELECT * FROM Diretor_de_Corrida WHERE id_utilizador=?', (session['id'],))
    if cursor.fetchone() is None:
        conn.close()
        return redirect('/logout')
    
    pesquisa = request.args.get('nome_procurado')
    
    # Only get events that are NOT finished (Por Iniciar, A Decorrer) and belong to current user
    query = "SELECT id_evento, nome, tipo, data_inicio, data_fim, status FROM Evento WHERE status != 'Concluído' AND ID_utilizador_gestor_de_corrida = ?"
    parametros = [session['id']]
    
    if pesquisa:
        query += " AND (nome LIKE ? OR tipo LIKE ?)"
        parametros.extend([f"%{pesquisa}%"] * 2)
    
    query += " ORDER BY data_inicio ASC"
    
    cursor.execute(query, tuple(parametros))
    eventos = cursor.fetchall()
    conn.close()
    
    return render_template('gerir_eventos.html', eventos=eventos, pesquisa_feita=pesquisa)

@app.route('/eventos_passados')
def eventos_passados():
    if 'loggedin' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify user is Diretor de Corrida
    cursor.execute('SELECT * FROM Diretor_de_Corrida WHERE id_utilizador=?', (session['id'],))
    if cursor.fetchone() is None:
        conn.close()
        return redirect('/logout')
    
    pesquisa = request.args.get('nome_procurado')
    
    # Only get finished events that belong to current user
    query = "SELECT id_evento, nome, tipo, data_inicio, data_fim, status FROM Evento WHERE status = 'Concluído' AND ID_utilizador_gestor_de_corrida = ?"
    parametros = [session['id']]
    
    if pesquisa:
        query += " AND (nome LIKE ? OR tipo LIKE ?)"
        parametros.extend([f"%{pesquisa}%"] * 2)
    
    query += " ORDER BY data_fim DESC"
    
    cursor.execute(query, tuple(parametros))
    eventos = cursor.fetchall()
    conn.close()
    
    return render_template('eventos_passados.html', eventos=eventos, pesquisa_feita=pesquisa)

# API endpoints for event management
@app.route('/api/evento/<int:id>', methods=['PUT'])
def editar_evento(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Only update if the event belongs to the current user
        cursor.execute(
            "UPDATE Evento SET nome=?, tipo=?, data_inicio=?, data_fim=?, status=? WHERE id_evento=? AND ID_utilizador_gestor_de_corrida=?",
            (data['nome'], data['tipo'], data['data_inicio'], data['data_fim'], data['status'], id, session['id'])
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Evento atualizado com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/evento/<int:id>', methods=['DELETE'])
def cancelar_evento(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Instead of deleting, set status to 'Cancelado' - only if event belongs to current user
        cursor.execute("UPDATE Evento SET status='Cancelado' WHERE id_evento=? AND ID_utilizador_gestor_de_corrida=?", (id, session['id']))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Evento cancelado com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/evento/<int:id>/status', methods=['PUT'])
def alterar_status_evento(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Only update if the event belongs to the current user
        cursor.execute("UPDATE Evento SET status=? WHERE id_evento=? AND ID_utilizador_gestor_de_corrida=?", (data['status'], id, session['id']))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Estado do evento atualizado!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/welcomeDE')
def welcomeDE():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Precisa fazer login para aceder a esta página!', 'redirect': '/login'}), 401
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Diretor_de_Equipa WHERE id_utilizador=?', (session['id'],))
    if cursor.fetchone() is None:
        conn.close()
        return redirect('/logout')
    
    # Verificar se o diretor já tem uma equipa
    cursor.execute('SELECT * FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
    equipa = cursor.fetchone()
    tem_equipa = equipa is not None
    conn.close()
    
    return render_template('welcomeDE.html', tem_equipa=tem_equipa, equipa=equipa)

@app.route('/pilotos_equipa')
def pilotos_equipa():
    if 'loggedin' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar se é diretor de equipa
    cursor.execute('SELECT * FROM Diretor_de_Equipa WHERE id_utilizador=?', (session['id'],))
    if cursor.fetchone() is None:
        conn.close()
        return redirect('/logout')
    
    # Obter a equipa do diretor
    cursor.execute('SELECT * FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
    equipa = cursor.fetchone()
    
    if equipa is None:
        conn.close()
        return redirect('/criar_equipa')
    
    # Obter pilotos da equipa
    cursor.execute('SELECT numero_licenca, nome, data_nascimento, nacionalidade FROM Piloto WHERE id_equipa=?', (equipa[0],))
    pilotos = cursor.fetchall()
    conn.close()
    
    return render_template('pilotos_equipa.html', equipa=equipa, pilotos=pilotos)

@app.route('/api/piloto', methods=['POST'])
def adicionar_piloto():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obter equipa do diretor
        cursor.execute('SELECT id_equipa FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
        equipa = cursor.fetchone()
        
        if equipa is None:
            conn.close()
            return jsonify({'success': False, 'message': 'Equipa não encontrada'}), 400
        
        cursor.execute(
            "INSERT INTO Piloto (numero_licenca, nome, data_nascimento, nacionalidade, id_equipa, numero_eventos) VALUES (?, ?, ?, ?, ?, 0)",
            (data['numero_licenca'], data['nome'], data['data_nascimento'], data['nacionalidade'], equipa[0])
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Piloto adicionado com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/piloto/<int:id>', methods=['PUT'])
def editar_piloto(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE Piloto SET nome=?, data_nascimento=?, nacionalidade=? WHERE numero_licenca=?",
            (data['nome'], data['data_nascimento'], data['nacionalidade'], id)
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Piloto atualizado com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/piloto/<int:id>', methods=['DELETE'])
def remover_piloto(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM Piloto WHERE numero_licenca=?", (id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Piloto removido com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/carros_equipa')
def carros_equipa():
    if 'loggedin' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar se é diretor de equipa
    cursor.execute('SELECT * FROM Diretor_de_Equipa WHERE id_utilizador=?', (session['id'],))
    if cursor.fetchone() is None:
        conn.close()
        return redirect('/logout')
    
    # Obter a equipa do diretor
    cursor.execute('SELECT * FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
    equipa = cursor.fetchone()
    
    if equipa is None:
        conn.close()
        return redirect('/criar_equipa')
    
    # Obter carros da equipa
    cursor.execute('SELECT VIN, modelo, marca, categoria, tipo_motor, potencia, peso FROM Carro WHERE id_equipa=?', (equipa[0],))
    carros = cursor.fetchall()
    conn.close()
    
    return render_template('carros_equipa.html', equipa=equipa, carros=carros)

@app.route('/api/carro', methods=['POST'])
def adicionar_carro():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obter equipa do diretor
        cursor.execute('SELECT id_equipa FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
        equipa = cursor.fetchone()
        
        if equipa is None:
            conn.close()
            return jsonify({'success': False, 'message': 'Equipa não encontrada'}), 400
        
        cursor.execute(
            "INSERT INTO Carro (VIN, modelo, marca, categoria, tipo_motor, potencia, peso, id_equipa) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (data['vin'], data['modelo'], data['marca'], data['categoria'], data['tipo_motor'], data['potencia'], data['peso'], equipa[0])
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Carro adicionado com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/carro/<path:vin>', methods=['PUT'])
def editar_carro(vin):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE Carro SET modelo=?, marca=?, categoria=?, tipo_motor=?, potencia=?, peso=? WHERE VIN=?",
            (data['modelo'], data['marca'], data['categoria'], data['tipo_motor'], data['potencia'], data['peso'], vin)
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Carro atualizado com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/carro/<path:vin>', methods=['DELETE'])
def remover_carro(vin):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM Carro WHERE VIN=?", (vin,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Carro removido com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/welcomeTP')
def welcomeTP():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Precisa fazer login para aceder a esta página!', 'redirect': '/login'}), 401 
    conn=get_db_connection()
    cursor=conn.cursor()
    cursor.execute('SELECT * FROM Tecnico_de_Pista WHERE id_utilizador=?',(session['id'],))
    if cursor.fetchone() is None:
        conn.close()
        return redirect('/logout')
    conn.close()
    return render_template('WelcomeTP.html')

# Define a rota para a página de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            data = request.get_json()
            username = data['username']
            password = data['password']
            conn = get_db_connection()  
            cursor = conn.cursor()
            cursor.execute('SELECT id_utilizador, username, email FROM Utilizador WHERE username = ? AND password = ?', (username, password))
            utilizador = cursor.fetchone()
            if utilizador:
                id_utilizador = utilizador[0]
                session['loggedin'] = True
                session['id'] = id_utilizador
                session['username'] = utilizador[1]

                cursor.execute('SELECT * FROM Tecnico_de_Pista WHERE id_utilizador = ?', (id_utilizador,))
                if cursor.fetchone():
                    session['role'] = 'tecnico'
                    conn.close()
                    return jsonify({'success': True, 'redirect': '/welcomeTP'})
                cursor.execute('SELECT * FROM Diretor_de_Equipa WHERE id_utilizador = ?', (id_utilizador,))
                if cursor.fetchone():
                    session['role'] = 'Diretor_de_Equipa'
                    conn.close()
                    return jsonify({'success': True, 'redirect': '/welcomeDE'})
                cursor.execute('SELECT * FROM Diretor_de_Corrida WHERE id_utilizador = ?', (id_utilizador,))
                if cursor.fetchone():
                    session['role'] = 'Diretor_de_Corrida'
                    conn.close()
                    return jsonify({'success': True, 'redirect': '/welcomeDC'})
                conn.close()
                return jsonify({'success': False, 'message': 'Utilizador sem tipo definido. Contacte o administrador.'}), 400
            else:
                conn.close()
                return jsonify({'success': False, 'message': 'Username ou password incorretos!'}), 401
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 400
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            data = request.get_json()
            nome = data['name']
            username = data['username']
            email = data['email']
            password = data['password']
            tipo = data['role']
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Inserir utilizador (ID é gerado automaticamente pelo IDENTITY)
            cursor.execute(
                "INSERT INTO Utilizador (username, email, password, nome) OUTPUT INSERTED.ID_utilizador VALUES (?, ?, ?, ?)",
                (username, email, password, nome)
            )
            id_utilizador = cursor.fetchone()[0]
            
            print(f"DEBUG: tipo recebido = '{tipo}'")
            print(f"DEBUG: id_utilizador = {id_utilizador}")
            
            if tipo == 'tecnico_de_pista':
                print("DEBUG: Inserindo em Tecnico_de_Pista")
                cursor.execute("INSERT INTO Tecnico_de_Pista (id_utilizador) VALUES (?)", (id_utilizador,))
            elif tipo == 'diretor_de_equipa':
                print("DEBUG: Inserindo em Diretor_de_Equipa")
                cursor.execute("INSERT INTO Diretor_de_Equipa (id_utilizador) VALUES (?)", (id_utilizador,))
            elif tipo == 'diretor_de_corrida':
                print("DEBUG: Inserindo em Diretor_de_Corrida")
                cursor.execute("INSERT INTO Diretor_de_Corrida (id_utilizador) VALUES (?)", (id_utilizador,))
            else:
                print(f"DEBUG: TIPO NÃO RECONHECIDO: '{tipo}'")
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Utilizador registado com sucesso!'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 400
    
    # GET request - retorna o template
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Executa o servidor apenas se o ficheiro for executado diretamente
if __name__ == '__main__':
    # Inicia o servidor Flask em modo debug (mostra erros detalhados)
    app.run(debug=True)