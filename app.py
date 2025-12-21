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

        query = """ SELECT P.numero_licenca, P.nome, P.data_nascimento, P.nacionalidade, E.nome AS nome_equipa, P.numero_eventos
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
            SELECT numero_licenca, nome, data_nascimento, nacionalidade 
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
        
        # garante que os status estão atualizados antes de listar
        cursor.execute("EXEC sp_ManutencaoStatusEventos")
        conn.commit()
        
        # lista os eventos com os totais 
        cursor.execute("EXEC sp_ListarEventosComTotais")
        eventos = cursor.fetchall()
        
        conn.close()
        return render_template('events.html', eventos=eventos)
    except Exception as e:
        return f"Erro: {e}"

@app.route('/api/lap_details/<int:id_volta>')
def lap_details(id_volta):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # query que junta a Volta com a Sessão para obter os dados técnicos
        query = """
            SELECT 
                S.temperatura_asfalto, S.temperatura_ar, S.humidade, S.precipitação,
                V.pressao_pneus, V.numero_volta, S.tipo as tipo_sessao,
                dbo.fn_FormatarTempoMS(V.tempo) as tempo
            FROM Volta V
            INNER JOIN Sessao S ON V.id_sessao = S.id_sessao
            WHERE V.id_volta = ?
        """
        cursor.execute(query, (id_volta,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return jsonify({
                'temp_asfalto': row[0], 'temp_ar': row[1],
                'humidade': row[2], 'precipitacao': row[3],
                'pressao': row[4], 'volta_n': row[5],
                'sessao': row[6], 'tempo': row[7]
            })
        return jsonify({'error': 'Não encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Define a rota para a página de recordes
@app.route('/records')
def records():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Obter listas para os dropdowns (Filtros Tradicionais)
        # Nota: ORDER BY deve coincidir com o SELECT DISTINCT para evitar o erro 42000
        cursor.execute("SELECT DISTINCT nome FROM Piloto ORDER BY nome")
        lista_pilotos = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT nome FROM Equipa ORDER BY nome")
        lista_equipas = [row[0] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT DISTINCT (marca + ' ' + modelo) 
            FROM Carro 
            ORDER BY (marca + ' ' + modelo)
        """)
        lista_carros = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT nome FROM Evento ORDER BY nome")
        lista_eventos = [row[0] for row in cursor.fetchall()]

        # 2. Capturar os filtros selecionados via GET
        f_piloto = request.args.get('piloto', '')
        f_equipa = request.args.get('equipa', '')
        f_carro = request.args.get('carro', '')
        f_evento = request.args.get('evento', '')

        # 3. Query Principal de Recordes usando a UDF fn_FormatarTempoMS
        query = """
            SELECT 
                dbo.fn_FormatarTempoMS(V.tempo) as tempo_formatado,
                P.nome as piloto,
                E.nome as equipa,
                C.marca + ' ' + C.modelo as carro,
                Ev.nome as evento,
                V.tempo,
                S.data,
                V.id_volta
            FROM Volta V
            INNER JOIN Piloto P ON V.numero_licenca = P.numero_licenca
            INNER JOIN Equipa E ON P.id_equipa = E.id_equipa
            INNER JOIN Carro C ON V.carro_VIN = C.VIN
            INNER JOIN Sessao S ON V.id_sessao = S.id_sessao
            INNER JOIN Evento Ev ON S.id_evento = Ev.id_evento
            WHERE 1=1
        """
        params = []

        # Aplicação dos filtros via Dropdowns (comparações exatas)
        if f_piloto:
            query += " AND P.nome = ?"
            params.append(f_piloto)
        if f_equipa:
            query += " AND E.nome = ?"
            params.append(f_equipa)
        if f_carro:
            query += " AND (C.marca + ' ' + C.modelo) = ?"
            params.append(f_carro)
        if f_evento:
            query += " AND Ev.nome = ?"
            params.append(f_evento)

        # Ordenar pelo tempo real (milissegundos) do mais rápido para o mais lento
        query += " ORDER BY V.tempo ASC"

        cursor.execute(query, params)
        recordes = cursor.fetchall()
        conn.close()

        # 4. Renderizar o template com todas as listas e filtros
        return render_template('records.html', 
                               recordes=recordes,
                               lista_pilotos=lista_pilotos,
                               lista_equipas=lista_equipas,
                               lista_carros=lista_carros,
                               lista_eventos=lista_eventos,
                               f_piloto=f_piloto,
                               f_equipa=f_equipa,
                               f_carro=f_carro,
                               f_evento=f_evento)
    except Exception as e:
        print(f"Erro detalhado nos recordes: {e}")
        return f"<h3>Erro ao carregar a página de recordes: {e}</h3>"

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
            
            # Insert event and get the new ID
            cursor.execute(
                "INSERT INTO Evento (nome, tipo, data_inicio, data_fim, status) OUTPUT INSERTED.id_evento VALUES (?, ?, ?, ?, ?)",
                (data['nome'], data['tipo'], data['data_inicio'], data['data_fim'], 'Por Iniciar')
            )
            id_evento = cursor.fetchone()[0]
            
            # Insert all sessions for this event
            sessoes = data.get('sessoes', [])
            for sessao in sessoes:
                cursor.execute(
                    """INSERT INTO Sessao (data, tipo, hora_inicio, hora_fim, id_evento) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (sessao['data'], sessao['tipo'], sessao['hora_inicio'], sessao['hora_fim'], id_evento)
                )
            
            conn.commit()
            conn.close()
            return jsonify({
                'success': True, 
                'message': f'Evento criado com sucesso com {len(sessoes)} sessão(ões)!', 
                'redirect': '/gerir_eventos'
            })
        except Exception as e:
            conn.rollback()
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
    
    # Only get events that are NOT finished (Por Iniciar, A Decorrer)
    query = "SELECT id_evento, nome, tipo, data_inicio, data_fim, status FROM Evento WHERE status != 'Concluído'"
    parametros = []
    
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
    
    # Only get finished events
    query = "SELECT id_evento, nome, tipo, data_inicio, data_fim, status FROM Evento WHERE status = 'Concluído'"
    parametros = []
    
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
        
        cursor.execute(
            "UPDATE Evento SET nome=?, tipo=?, data_inicio=?, data_fim=?, status=? WHERE id_evento=?",
            (data['nome'], data['tipo'], data['data_inicio'], data['data_fim'], data['status'], id)
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
        
        # First delete all sessions associated with this event
        cursor.execute("DELETE FROM Sessao WHERE id_evento=?", (id,))
        
        # Then delete the event
        cursor.execute("DELETE FROM Evento WHERE id_evento=?", (id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Evento apagado com sucesso!'})
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
        
        cursor.execute("UPDATE Evento SET status=? WHERE id_evento=?", (data['status'], id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Estado do evento atualizado!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# API endpoint to get event details
@app.route('/api/evento/<int:id>', methods=['GET'])
def obter_evento(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id_evento, nome, tipo, data_inicio, data_fim, status FROM Evento WHERE id_evento=?", (id,))
        evento = cursor.fetchone()
        conn.close()
        
        if evento:
            return jsonify({
                'success': True,
                'evento': {
                    'id': evento[0],
                    'nome': evento[1],
                    'tipo': evento[2],
                    'data_inicio': str(evento[3]),
                    'data_fim': str(evento[4]),
                    'status': evento[5]
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Evento não encontrado'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# API endpoint to get sessions for an event
@app.route('/api/evento/<int:id>/sessoes')
def obter_sessoes_evento(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id_sessao, data, tipo, hora_inicio, hora_fim, status 
            FROM Sessao 
            WHERE id_evento=? 
            ORDER BY data, hora_inicio
        """, (id,))
        sessoes = cursor.fetchall()
        conn.close()
        
        sessoes_list = []
        for s in sessoes:
            sessoes_list.append({
                'id': s[0],
                'data': str(s[1]),
                'tipo': s[2],
                'hora_inicio': str(s[3])[:5] if s[3] else '',
                'hora_fim': str(s[4])[:5] if s[4] else '',
                'status': s[5] if s[5] else 'Por Iniciar'
            })
        
        return jsonify({'success': True, 'sessoes': sessoes_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# API endpoint to update session status
@app.route('/api/sessao/<int:id>/status', methods=['PUT'])
def alterar_status_sessao(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE Sessao SET status=? WHERE id_sessao=?", (data['status'], id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Estado da sessão atualizado!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# API endpoint to create a new session
@app.route('/api/sessao', methods=['POST'])
def criar_sessao():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO Sessao (data, tipo, hora_inicio, hora_fim, id_evento) 
               VALUES (?, ?, ?, ?, ?)""",
            (data['data'], data['tipo'], data['hora_inicio'], data['hora_fim'], data['id_evento'])
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Sessão criada com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# API endpoint to update a session
@app.route('/api/sessao/<int:id>', methods=['PUT'])
def editar_sessao(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """UPDATE Sessao SET data=?, tipo=?, hora_inicio=?, hora_fim=? 
               WHERE id_sessao=?""",
            (data['data'], data['tipo'], data['hora_inicio'], data['hora_fim'], id)
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Sessão atualizada com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# API endpoint to delete a session
@app.route('/api/sessao/<int:id>', methods=['DELETE'])
def remover_sessao(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM Sessao WHERE id_sessao=?", (id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Sessão removida com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# Route for team to view and register for events
@app.route('/eventos_equipa')
def eventos_equipa():
    if 'loggedin' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify user is Diretor de Equipa
    cursor.execute('SELECT * FROM Diretor_de_Equipa WHERE id_utilizador=?', (session['id'],))
    if cursor.fetchone() is None:
        conn.close()
        return redirect('/logout')
    
    # Get team
    cursor.execute('SELECT * FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
    equipa = cursor.fetchone()
    
    if equipa is None:
        conn.close()
        return redirect('/criar_equipa')
    
    id_equipa = equipa[0]
    
    # Get all events that are not finished, with info about team registration
    cursor.execute("""
        SELECT e.id_evento, e.nome, e.tipo, e.data_inicio, e.data_fim, e.status,
               CASE WHEN pe.id_equipa IS NOT NULL THEN 1 ELSE 0 END as inscrito,
               (SELECT COUNT(*) FROM Sessao s WHERE s.id_evento = e.id_evento) as num_sessoes
        FROM Evento e
        LEFT JOIN Participa_Evento pe ON e.id_evento = pe.id_evento AND pe.id_equipa = ?
        WHERE e.status IN ('Por Iniciar', 'A Decorrer')
        ORDER BY e.data_inicio ASC
    """, (id_equipa,))
    
    eventos_raw = cursor.fetchall()
    conn.close()
    
    eventos = []
    for e in eventos_raw:
        eventos.append({
            'id': e[0],
            'nome': e[1],
            'tipo': e[2],
            'data_inicio': str(e[3]),
            'data_fim': str(e[4]),
            'status': e[5],
            'inscrito': e[6] == 1,
            'num_sessoes': e[7]
        })
    
    return render_template('eventos_equipa.html', equipa=equipa, eventos=eventos)

# Route for team to view events they are participating in
@app.route('/eventos_atuais')
def eventos_atuais():
    if 'loggedin' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify user is Diretor de Equipa
    cursor.execute('SELECT * FROM Diretor_de_Equipa WHERE id_utilizador=?', (session['id'],))
    if cursor.fetchone() is None:
        conn.close()
        return redirect('/logout')
    
    # Get team
    cursor.execute('SELECT * FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
    equipa = cursor.fetchone()
    
    if equipa is None:
        conn.close()
        return redirect('/criar_equipa')
    
    id_equipa = equipa[0]
    
    # Get events the team is registered for
    cursor.execute("""
        SELECT e.id_evento, e.nome, e.tipo, e.data_inicio, e.data_fim, e.status
        FROM Evento e
        INNER JOIN Participa_Evento pe ON e.id_evento = pe.id_evento
        WHERE pe.id_equipa = ? AND e.status IN ('Por Iniciar', 'A Decorrer')
        ORDER BY e.data_inicio ASC
    """, (id_equipa,))
    
    eventos_raw = cursor.fetchall()
    conn.close()
    
    eventos = []
    for e in eventos_raw:
        eventos.append({
            'id': e[0],
            'nome': e[1],
            'tipo': e[2],
            'data_inicio': str(e[3]),
            'data_fim': str(e[4]),
            'status': e[5]
        })
    
    return render_template('eventos_atuais.html', equipa=equipa, eventos=eventos)

# API endpoint to register team for event
@app.route('/api/inscricao', methods=['POST'])
def inscrever_evento():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get team
        cursor.execute('SELECT id_equipa FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
        equipa = cursor.fetchone()
        
        if equipa is None:
            conn.close()
            return jsonify({'success': False, 'message': 'Equipa não encontrada'}), 400
        
        cursor.execute(
            "INSERT INTO Participa_Evento (id_equipa, id_evento) VALUES (?, ?)",
            (equipa[0], data['id_evento'])
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Inscrição efetuada com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# API endpoint to cancel team registration for event
@app.route('/api/inscricao/<int:id_evento>', methods=['DELETE'])
def cancelar_inscricao(id_evento):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get team
        cursor.execute('SELECT id_equipa FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
        equipa = cursor.fetchone()
        
        if equipa is None:
            conn.close()
            return jsonify({'success': False, 'message': 'Equipa não encontrada'}), 400
        
        id_equipa = equipa[0]
        
        # Check if there are pilots/cars from this team registered in sessions of this event
        cursor.execute("""
            SELECT COUNT(*) 
            FROM Participa_Sessao ps
            INNER JOIN Sessao s ON ps.id_sessao = s.id_sessao
            INNER JOIN Piloto p ON ps.numero_licenca = p.numero_licenca
            WHERE s.id_evento = ? AND p.id_equipa = ?
        """, (id_evento, id_equipa))
        
        count = cursor.fetchone()[0]
        
        if count > 0:
            conn.close()
            return jsonify({
                'success': False, 
                'message': 'Não é possível cancelar a inscrição. Existem pilotos inscritos em sessões deste evento. Remova primeiro as inscrições nas sessões.'
            }), 400
        
        cursor.execute(
            "DELETE FROM Participa_Evento WHERE id_equipa=? AND id_evento=?",
            (id_equipa, id_evento)
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Inscrição cancelada com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# Route for session registration page
@app.route('/inscricao_sessao')
def inscricao_sessao():
    if 'loggedin' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify user is Diretor de Equipa
    cursor.execute('SELECT * FROM Diretor_de_Equipa WHERE id_utilizador=?', (session['id'],))
    if cursor.fetchone() is None:
        conn.close()
        return redirect('/logout')
    
    # Get team
    cursor.execute('SELECT * FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
    equipa = cursor.fetchone()
    
    if equipa is None:
        conn.close()
        return redirect('/criar_equipa')
    
    id_equipa = equipa[0]
    
    # Get events the team is registered for ('Por Iniciar' or 'A Decorrer')
    cursor.execute("""
        SELECT e.id_evento, e.nome, e.tipo, e.data_inicio, e.data_fim, e.status
        FROM Evento e
        INNER JOIN Participa_Evento pe ON e.id_evento = pe.id_evento
        WHERE pe.id_equipa = ? AND e.status IN ('Por Iniciar', 'A Decorrer')
        ORDER BY e.data_inicio ASC
    """, (id_equipa,))
    
    eventos_raw = cursor.fetchall()
    
    eventos = []
    for e in eventos_raw:
        eventos.append({
            'id': e[0],
            'nome': e[1],
            'tipo': e[2],
            'data_inicio': str(e[3]),
            'data_fim': str(e[4]),
            'status': e[5]
        })
    
    # Get team's pilots
    cursor.execute('SELECT numero_licenca, nome FROM Piloto WHERE id_equipa=?', (id_equipa,))
    pilotos = cursor.fetchall()
    
    # Get team's cars
    cursor.execute('SELECT VIN, modelo, marca FROM Carro WHERE id_equipa=?', (id_equipa,))
    carros = cursor.fetchall()
    
    conn.close()
    
    return render_template('inscricao_sessao.html', equipa=equipa, eventos=eventos, pilotos=pilotos, carros=carros)

# API endpoint to get sessions with inscriptions for an event
@app.route('/api/evento/<int:id>/sessoes_inscricao')
def obter_sessoes_inscricao(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get team
        cursor.execute('SELECT id_equipa FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
        equipa = cursor.fetchone()
        
        if equipa is None:
            conn.close()
            return jsonify({'success': False, 'message': 'Equipa não encontrada'}), 400
        
        id_equipa = equipa[0]
        
        # Get sessions for this event with status
        cursor.execute("""
            SELECT id_sessao, data, tipo, hora_inicio, hora_fim, status 
            FROM Sessao 
            WHERE id_evento=? 
            ORDER BY data, hora_inicio
        """, (id,))
        sessoes = cursor.fetchall()
        
        sessoes_list = []
        previous_completed = True  # First session can always be registered
        
        for s in sessoes:
            # Get inscriptions for this session (only from this team)
            cursor.execute("""
                SELECT ps.numero_licenca, ps.VIN_carro, p.nome, c.marca, c.modelo
                FROM Participa_Sessao ps
                INNER JOIN Piloto p ON ps.numero_licenca = p.numero_licenca
                INNER JOIN Carro c ON ps.VIN_carro = c.VIN
                WHERE ps.id_sessao = ? AND p.id_equipa = ?
            """, (s[0], id_equipa))
            inscricoes = cursor.fetchall()
            
            inscricoes_list = []
            for insc in inscricoes:
                inscricoes_list.append({
                    'piloto_licenca': insc[0],
                    'carro_vin': insc[1],
                    'piloto_nome': insc[2],
                    'carro_marca': insc[3],
                    'carro_modelo': insc[4]
                })
            
            sessao_status = s[5] if s[5] else 'Por Iniciar'
            
            # Can only register if previous session is completed (or this is the first session)
            pode_inscrever = previous_completed and sessao_status != 'Concluída'
            
            sessoes_list.append({
                'id': s[0],
                'data': str(s[1]),
                'tipo': s[2],
                'hora_inicio': str(s[3])[:5] if s[3] else '',
                'hora_fim': str(s[4])[:5] if s[4] else '',
                'status': sessao_status,
                'pode_inscrever': pode_inscrever,
                'inscricoes': inscricoes_list
            })
            
            # Update for next iteration: previous is completed only if this session is completed
            previous_completed = (sessao_status == 'Concluída')
        
        conn.close()
        return jsonify({'success': True, 'sessoes': sessoes_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# API endpoint to create session participation
@app.route('/api/participacao_sessao', methods=['POST'])
def criar_participacao_sessao():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if pilot is already registered in this session
        cursor.execute("""
            SELECT * FROM Participa_Sessao 
            WHERE id_sessao=? AND numero_licenca=?
        """, (data['id_sessao'], data['numero_licenca']))
        if cursor.fetchone() is not None:
            conn.close()
            return jsonify({'success': False, 'message': 'Este piloto já está inscrito nesta sessão!'}), 400
        
        # Check if car is already registered in this session
        cursor.execute("""
            SELECT * FROM Participa_Sessao 
            WHERE id_sessao=? AND VIN_carro=?
        """, (data['id_sessao'], data['VIN_carro']))
        if cursor.fetchone() is not None:
            conn.close()
            return jsonify({'success': False, 'message': 'Este carro já está inscrito nesta sessão!'}), 400
        
        cursor.execute("""
            INSERT INTO Participa_Sessao (id_sessao, numero_licenca, VIN_carro, combustivel_inicial, pressao_pneus, configuracao_aerodinamica)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data['id_sessao'],
            data['numero_licenca'],
            data['VIN_carro'],
            data['combustivel_inicial'],
            data['pressao_pneus'],
            data['configuracao_aerodinamica']
        ))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Inscrição na sessão efetuada com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# API endpoint to delete session participation
@app.route('/api/participacao_sessao', methods=['DELETE'])
def remover_participacao_sessao():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM Participa_Sessao 
            WHERE id_sessao=? AND numero_licenca=? AND VIN_carro=?
        """, (data['id_sessao'], data['numero_licenca'], data['VIN_carro']))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Inscrição removida com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/criar_equipa', methods=['GET', 'POST'])
def criar_equipa():
    if 'loggedin' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify user is Diretor de Equipa
    cursor.execute('SELECT * FROM Diretor_de_Equipa WHERE id_utilizador=?', (session['id'],))
    if cursor.fetchone() is None:
        conn.close()
        return redirect('/logout')
    
    # Check if director already has a team
    cursor.execute('SELECT * FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
    if cursor.fetchone() is not None:
        conn.close()
        return redirect('/welcomeDE')
    
    if request.method == 'GET':
        conn.close()
        return render_template('criar_equipa.html')
    
    # POST - Create team
    try:
        data = request.get_json()
        cursor.execute(
            "INSERT INTO Equipa (nome, pais, ID_utilizador_diretor_de_equipa) VALUES (?, ?, ?)",
            (data['nome'], data['pais'], session['id'])
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Equipa criada com sucesso!', 'redirect': '/welcomeDE'})
    except Exception as e:
        conn.close()
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
    return render_template('WelcomeTP.html', username=session.get('username', 'Técnico'))

@app.route('/registar_voltas')
def registar_voltas():
    if 'loggedin' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify user is Tecnico de Pista
    cursor.execute('SELECT * FROM Tecnico_de_Pista WHERE id_utilizador=?', (session['id'],))
    if cursor.fetchone() is None:
        conn.close()
        return redirect('/logout')
    
    # Get sessions from active events (A Decorrer)
    cursor.execute("""
        SELECT s.id_sessao, s.data, s.tipo, s.hora_inicio, s.hora_fim, s.status, e.nome as evento_nome
        FROM Sessao s
        INNER JOIN Evento e ON s.id_evento = e.id_evento
        WHERE e.status = 'A Decorrer' AND s.status IN ('Por Iniciar', 'A Decorrer')
        ORDER BY s.data, s.hora_inicio
    """)
    
    sessoes_raw = cursor.fetchall()
    conn.close()
    
    sessoes = []
    for s in sessoes_raw:
        sessoes.append({
            'id': s[0],
            'data': str(s[1]),
            'tipo': s[2],
            'hora_inicio': str(s[3])[:5] if s[3] else '',
            'hora_fim': str(s[4])[:5] if s[4] else '',
            'status': s[5] if s[5] else 'Por Iniciar',
            'evento_nome': s[6]
        })
    
    return render_template('registar_voltas.html', sessoes=sessoes)

# API endpoint to get participants of a session
@app.route('/api/sessao/<int:id>/participantes')
def obter_participantes_sessao(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get participants with pilot and car info, including tire pressure from Participa_Sessao
        cursor.execute("""
            SELECT ps.numero_licenca, ps.VIN_carro, p.nome as piloto_nome, c.marca, c.modelo,
                   (SELECT COUNT(*) FROM Volta v WHERE v.id_sessao=ps.id_sessao AND v.numero_licenca=ps.numero_licenca AND v.carro_VIN=ps.VIN_carro) as voltas_count,
                   ps.pressao_pneus
            FROM Participa_Sessao ps
            INNER JOIN Piloto p ON ps.numero_licenca = p.numero_licenca
            INNER JOIN Carro c ON ps.VIN_carro = c.VIN
            WHERE ps.id_sessao = ?
        """, (id,))
        
        participantes = cursor.fetchall()
        conn.close()
        
        participantes_list = []
        for p in participantes:
            participantes_list.append({
                'piloto_licenca': p[0],
                'carro_vin': p[1],
                'piloto_nome': p[2],
                'carro_marca': p[3],
                'carro_modelo': p[4],
                'voltas_count': p[5],
                'pressao_pneus': p[6] if p[6] else 28
            })
        
        return jsonify({'success': True, 'participantes': participantes_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# API endpoint to register a lap
@app.route('/api/volta', methods=['POST'])
def registar_volta():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if lap number already exists for this car in this session
        cursor.execute("""
            SELECT * FROM Volta 
            WHERE id_sessao=? AND carro_VIN=? AND numero_volta=?
        """, (data['id_sessao'], data['carro_VIN'], data['numero_volta']))
        if cursor.fetchone() is not None:
            conn.close()
            return jsonify({'success': False, 'message': 'Já existe uma volta com este número para este carro nesta sessão!'}), 400
        
        # Check if weather conditions are registered for this session
        cursor.execute("""
            SELECT temperatura_asfalto, temperatura_ar, humidade 
            FROM Sessao WHERE id_sessao=?
        """, (data['id_sessao'],))
        sessao = cursor.fetchone()
        if sessao is None or sessao[0] is None or sessao[1] is None or sessao[2] is None:
            conn.close()
            return jsonify({
                'success': False, 
                'message': 'Não é possível registar voltas. As condições meteorológicas da sessão ainda não foram registadas.'
            }), 400
        
        # Get tire pressure from Participa_Sessao
        cursor.execute("""
            SELECT pressao_pneus FROM Participa_Sessao 
            WHERE id_sessao=? AND VIN_carro=?
        """, (data['id_sessao'], data['carro_VIN']))
        participa = cursor.fetchone()
        pressao_pneus = participa[0] if participa and participa[0] else 28
        
        # Use stored procedure to register lap (converts time format automatically)
        cursor.execute("""
            EXEC sp_RegistarVolta ?, ?, ?, ?, ?, ?, ?
        """, (
            data['id_sessao'],
            data['numero_licenca'],
            data['carro_VIN'],
            data['tempo'],  # Format: mm:ss:ms
            data['numero_volta'],
            pressao_pneus,
            session['id']
        ))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Volta registada com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400



@app.route('/condicoes_pista')
def condicoes_pista():
    if 'loggedin' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify user is Tecnico de Pista
    cursor.execute('SELECT * FROM Tecnico_de_Pista WHERE id_utilizador=?', (session['id'],))
    if cursor.fetchone() is None:
        conn.close()
        return redirect('/logout')
    
    # Get active sessions (from events that are 'A Decorrer')
    cursor.execute("""
        SELECT s.id_sessao, s.data, s.tipo, s.hora_inicio, s.hora_fim,
               s.temperatura_asfalto, s.temperatura_ar, s.humidade, s.precipitação,
               e.nome as evento_nome
        FROM Sessao s
        INNER JOIN Evento e ON s.id_evento = e.id_evento
        WHERE e.status = 'A Decorrer'
        ORDER BY s.data, s.hora_inicio
    """)
    
    sessoes_raw = cursor.fetchall()
    conn.close()
    
    sessoes = []
    for s in sessoes_raw:
        sessoes.append({
            'id': s[0],
            'data': str(s[1]),
            'tipo': s[2],
            'hora_inicio': str(s[3])[:5] if s[3] else '',
            'hora_fim': str(s[4])[:5] if s[4] else '',
            'temperatura_asfalto': s[5],
            'temperatura_ar': s[6],
            'humidade': s[7],
            'precipitacao': s[8],
            'evento_nome': s[9]
        })
    
    return render_template('condicoes_pista.html', sessoes=sessoes)

@app.route('/api/sessao/<int:id>/condicoes', methods=['PUT'])
def atualizar_condicoes_sessao(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE Sessao 
            SET temperatura_asfalto=?, temperatura_ar=?, humidade=?, precipitação=?
            WHERE id_sessao=?
        """, (
            data.get('temperatura_asfalto'),
            data.get('temperatura_ar'),
            data.get('humidade'),
            data.get('precipitacao'),
            id
        ))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Condições atualizadas com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


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