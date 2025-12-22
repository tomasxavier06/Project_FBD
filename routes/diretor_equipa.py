# Rotas do Diretor de Equipa
from flask import Blueprint, render_template, request, jsonify, session, redirect
from utils.database import get_db

de_bp = Blueprint('diretor_equipa', __name__)


@de_bp.route('/welcomeDE')
def welcomeDE():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Precisa fazer login para aceder a esta página!', 'redirect': '/login'}), 401
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Diretor_de_Equipa WHERE id_utilizador=?', (session['id'],))
        if cursor.fetchone() is None:
            return redirect('/logout')
        
        # Verificar se o diretor já tem uma equipa
        cursor.execute('SELECT * FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
        equipa = cursor.fetchone()
        tem_equipa = equipa is not None
    
    return render_template('welcomeDE.html', tem_equipa=tem_equipa, equipa=equipa)


@de_bp.route('/criar_equipa', methods=['GET', 'POST'])
def criar_equipa():
    if 'loggedin' not in session:
        return redirect('/login')
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Verify user is Diretor de Equipa
        cursor.execute('SELECT * FROM Diretor_de_Equipa WHERE id_utilizador=?', (session['id'],))
        if cursor.fetchone() is None:
            return redirect('/logout')
        
        # Check if director already has a team
        cursor.execute('SELECT * FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
        if cursor.fetchone() is not None:
            return redirect('/welcomeDE')
        
        if request.method == 'GET':
            return render_template('criar_equipa.html')
        
        # POST - Create team
        try:
            data = request.get_json()
            # Usar Stored Procedure para criar equipa
            cursor.execute(
                'EXEC sp_CriarEquipa ?, ?, ?',
                (data['nome'], data['pais'], session['id'])
            )
            conn.commit()
            return jsonify({'success': True, 'message': 'Equipa criada com sucesso!', 'redirect': '/welcomeDE'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 400


@de_bp.route('/pilotos_equipa')
def pilotos_equipa():
    if 'loggedin' not in session:
        return redirect('/login')
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Verificar se é diretor de equipa
        cursor.execute('SELECT * FROM Diretor_de_Equipa WHERE id_utilizador=?', (session['id'],))
        if cursor.fetchone() is None:
            return redirect('/logout')
        
        # Obter a equipa do diretor
        cursor.execute('SELECT * FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
        equipa = cursor.fetchone()
        
        if equipa is None:
            return redirect('/criar_equipa')
        
        # Obter pilotos da equipa
        cursor.execute('SELECT numero_licenca, nome, data_nascimento, nacionalidade FROM Piloto WHERE id_equipa=?', (equipa[0],))
        pilotos = cursor.fetchall()
    
    return render_template('pilotos_equipa.html', equipa=equipa, pilotos=pilotos)


@de_bp.route('/api/piloto', methods=['POST'])
def adicionar_piloto():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Obter equipa do diretor
            cursor.execute('SELECT id_equipa FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
            equipa = cursor.fetchone()
            
            if equipa is None:
                return jsonify({'success': False, 'message': 'Equipa não encontrada'}), 400
            
            # Usar Stored Procedures
            if data.get('vincular_existente'):
                cursor.execute('EXEC sp_VincularPiloto ?, ?', (data['numero_licenca'], equipa[0]))
            else:
                cursor.execute('EXEC sp_AdicionarPiloto ?, ?, ?, ?, ?', 
                    (data['numero_licenca'], data['nome'], data['data_nascimento'], data['nacionalidade'], equipa[0]))
            
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Piloto adicionado com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@de_bp.route('/api/pilotos_disponiveis')
def pilotos_disponiveis():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT numero_licenca, nome, data_nascimento, nacionalidade, numero_eventos 
                FROM Piloto WHERE id_equipa IS NULL
                ORDER BY nome
            """)
            pilotos = cursor.fetchall()
        
        pilotos_list = []
        for p in pilotos:
            pilotos_list.append({
                'numero_licenca': p[0],
                'nome': p[1],
                'data_nascimento': str(p[2]) if p[2] else '',
                'nacionalidade': p[3],
                'numero_eventos': p[4]
            })
        
        return jsonify({'success': True, 'pilotos': pilotos_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@de_bp.route('/api/piloto/<int:id>', methods=['PUT'])
def editar_piloto(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        
        with get_db() as conn:
            cursor = conn.cursor()
            # Usar Stored Procedure para atualizar piloto
            cursor.execute(
                'EXEC sp_AtualizarPiloto ?, ?, ?, ?',
                (id, data['nome'], data['data_nascimento'], data['nacionalidade'])
            )
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Piloto atualizado com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@de_bp.route('/api/piloto/<int:id>', methods=['DELETE'])
def remover_piloto(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Get the team of the director
            cursor.execute('SELECT id_equipa FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
            equipa = cursor.fetchone()
            
            if equipa is None:
                return jsonify({'success': False, 'message': 'Equipa não encontrada'}), 400
            
            id_equipa = equipa[0]
            
            # Usar Stored Procedure para desvincular piloto (já valida eventos ativos)
            cursor.execute('EXEC sp_DesvincularPiloto ?, ?', (id, id_equipa))
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Piloto desvinculado da equipa com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@de_bp.route('/carros_equipa')
def carros_equipa():
    if 'loggedin' not in session:
        return redirect('/login')
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Verificar se é diretor de equipa
        cursor.execute('SELECT * FROM Diretor_de_Equipa WHERE id_utilizador=?', (session['id'],))
        if cursor.fetchone() is None:
            return redirect('/logout')
        
        # Obter a equipa do diretor
        cursor.execute('SELECT * FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
        equipa = cursor.fetchone()
        
        if equipa is None:
            return redirect('/criar_equipa')
        
        # Obter carros da equipa
        cursor.execute('SELECT VIN, modelo, marca, categoria, tipo_motor, potencia, peso FROM Carro WHERE id_equipa=?', (equipa[0],))
        carros = cursor.fetchall()
    
    return render_template('carros_equipa.html', equipa=equipa, carros=carros)


@de_bp.route('/api/carro', methods=['POST'])
def adicionar_carro():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Obter equipa do diretor
            cursor.execute('SELECT id_equipa FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
            equipa = cursor.fetchone()
            
            if equipa is None:
                return jsonify({'success': False, 'message': 'Equipa não encontrada'}), 400
            
            # Usar Stored Procedures
            if data.get('vincular_existente'):
                cursor.execute('EXEC sp_VincularCarro ?, ?', (data['vin'], equipa[0]))
            else:
                cursor.execute('EXEC sp_AdicionarCarro ?, ?, ?, ?, ?, ?, ?, ?', 
                    (data['vin'], data['modelo'], data['marca'], data['categoria'], 
                     data['tipo_motor'], data['potencia'], data['peso'], equipa[0]))
            
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Carro adicionado com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@de_bp.route('/api/carros_disponiveis')
def carros_disponiveis():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT VIN, modelo, marca, categoria, tipo_motor, potencia, peso 
                FROM Carro WHERE id_equipa IS NULL
                ORDER BY marca, modelo
            """)
            carros = cursor.fetchall()
        
        carros_list = []
        for c in carros:
            carros_list.append({
                'vin': c[0],
                'modelo': c[1],
                'marca': c[2],
                'categoria': c[3],
                'tipo_motor': c[4],
                'potencia': c[5],
                'peso': c[6]
            })
        
        return jsonify({'success': True, 'carros': carros_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@de_bp.route('/api/carro/<path:vin>', methods=['PUT'])
def editar_carro(vin):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        
        with get_db() as conn:
            cursor = conn.cursor()
            # Usar Stored Procedure para atualizar carro
            cursor.execute(
                'EXEC sp_AtualizarCarro ?, ?, ?, ?, ?, ?, ?',
                (vin, data['modelo'], data['marca'], data['categoria'], data['tipo_motor'], data['potencia'], data['peso'])
            )
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Carro atualizado com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@de_bp.route('/api/carro/<path:vin>', methods=['DELETE'])
def remover_carro(vin):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Get the team of the director
            cursor.execute('SELECT id_equipa FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
            equipa = cursor.fetchone()
            
            if equipa is None:
                return jsonify({'success': False, 'message': 'Equipa não encontrada'}), 400
            
            id_equipa = equipa[0]
            
            # Usar Stored Procedure para desvincular carro (já valida eventos ativos)
            cursor.execute('EXEC sp_DesvincularCarro ?, ?', (vin, id_equipa))
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Carro desvinculado da equipa com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@de_bp.route('/eventos_equipa')
def eventos_equipa():
    if 'loggedin' not in session:
        return redirect('/login')
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Verify user is Diretor de Equipa
        cursor.execute('SELECT * FROM Diretor_de_Equipa WHERE id_utilizador=?', (session['id'],))
        if cursor.fetchone() is None:
            return redirect('/logout')
        
        # Get team
        cursor.execute('SELECT * FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
        equipa = cursor.fetchone()
        
        if equipa is None:
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


@de_bp.route('/eventos_atuais')
def eventos_atuais():
    if 'loggedin' not in session:
        return redirect('/login')
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Verify user is Diretor de Equipa
        cursor.execute('SELECT * FROM Diretor_de_Equipa WHERE id_utilizador=?', (session['id'],))
        if cursor.fetchone() is None:
            return redirect('/logout')
        
        # Get team
        cursor.execute('SELECT * FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
        equipa = cursor.fetchone()
        
        if equipa is None:
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


@de_bp.route('/api/inscricao', methods=['POST'])
def inscrever_evento():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Get team
            cursor.execute('SELECT id_equipa FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
            equipa = cursor.fetchone()
            
            if equipa is None:
                return jsonify({'success': False, 'message': 'Equipa não encontrada'}), 400
            
            # Usar Stored Procedure para inscrever equipa
            cursor.execute('EXEC sp_InscreverEquipaEvento ?, ?', (equipa[0], data['id_evento']))
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Inscrição efetuada com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@de_bp.route('/api/inscricao/<int:id_evento>', methods=['DELETE'])
def cancelar_inscricao(id_evento):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Get team
            cursor.execute('SELECT id_equipa FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
            equipa = cursor.fetchone()
            
            if equipa is None:
                return jsonify({'success': False, 'message': 'Equipa não encontrada'}), 400
            
            id_equipa = equipa[0]
            
            # Usar Stored Procedure para cancelar inscrição (já valida sessões)
            cursor.execute('EXEC sp_CancelarInscricaoEvento ?, ?', (id_equipa, id_evento))
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Inscrição cancelada com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@de_bp.route('/inscricao_sessao')
def inscricao_sessao():
    if 'loggedin' not in session:
        return redirect('/login')
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Verify user is Diretor de Equipa
        cursor.execute('SELECT * FROM Diretor_de_Equipa WHERE id_utilizador=?', (session['id'],))
        if cursor.fetchone() is None:
            return redirect('/logout')
        
        # Get team
        cursor.execute('SELECT * FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
        equipa = cursor.fetchone()
        
        if equipa is None:
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
    
    return render_template('inscricao_sessao.html', equipa=equipa, eventos=eventos, pilotos=pilotos, carros=carros)


@de_bp.route('/api/evento/<int:id>/sessoes_inscricao')
def obter_sessoes_inscricao(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Get team
            cursor.execute('SELECT id_equipa FROM Equipa WHERE ID_utilizador_diretor_de_equipa=?', (session['id'],))
            equipa = cursor.fetchone()
            
            if equipa is None:
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
            previous_completed = True
            
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
                
                previous_completed = (sessao_status == 'Concluída')
        
        return jsonify({'success': True, 'sessoes': sessoes_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@de_bp.route('/api/participacao_sessao', methods=['POST'])
def criar_participacao_sessao():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        
        with get_db() as conn:
            cursor = conn.cursor()
            # Usar Stored Procedure para inscrever em sessão (já valida duplicados e status)
            cursor.execute('EXEC sp_InscreverSessao ?, ?, ?, ?, ?, ?', (
                data['id_sessao'],
                data['numero_licenca'],
                data['VIN_carro'],
                data['combustivel_inicial'],
                data['pressao_pneus'],
                data['configuracao_aerodinamica']
            ))
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Inscrição na sessão efetuada com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@de_bp.route('/api/participacao_sessao', methods=['DELETE'])
def remover_participacao_sessao():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        
        with get_db() as conn:
            cursor = conn.cursor()
            # Usar Stored Procedure para cancelar inscrição (já valida status)
            cursor.execute('EXEC sp_CancelarInscricaoSessao ?, ?, ?', (
                data['id_sessao'],
                data['numero_licenca'],
                data['VIN_carro']
            ))
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Inscrição removida com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400
