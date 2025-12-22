# Rotas do Técnico de Pista
from flask import Blueprint, render_template, request, jsonify, session, redirect
from utils.database import get_db

tp_bp = Blueprint('tecnico_pista', __name__)


@tp_bp.route('/welcomeTP')
def welcomeTP():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Precisa fazer login para aceder a esta página!', 'redirect': '/login'}), 401
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Tecnico_de_Pista WHERE id_utilizador=?', (session['id'],))
        if cursor.fetchone() is None:
            return redirect('/logout')
    
    return render_template('WelcomeTP.html', username=session.get('username', 'Técnico'))


@tp_bp.route('/registar_voltas')
def registar_voltas():
    if 'loggedin' not in session:
        return redirect('/login')
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Verify user is Tecnico de Pista
        cursor.execute('SELECT * FROM Tecnico_de_Pista WHERE id_utilizador=?', (session['id'],))
        if cursor.fetchone() is None:
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


@tp_bp.route('/api/sessao/<int:id>/participantes')
def obter_participantes_sessao(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        with get_db() as conn:
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


@tp_bp.route('/api/volta', methods=['POST'])
def registar_volta():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Check if lap number already exists for this car in this session
            cursor.execute("""
                SELECT * FROM Volta 
                WHERE id_sessao=? AND carro_VIN=? AND numero_volta=?
            """, (data['id_sessao'], data['carro_VIN'], data['numero_volta']))
            if cursor.fetchone() is not None:
                return jsonify({'success': False, 'message': 'Já existe uma volta com este número para este carro nesta sessão!'}), 400
            
            # Check if weather conditions are registered AND session is in progress
            cursor.execute("""
                SELECT temperatura_asfalto, temperatura_ar, humidade, status 
                FROM Sessao WHERE id_sessao=?
            """, (data['id_sessao'],))
            sessao = cursor.fetchone()
            
            if sessao is None:
                return jsonify({'success': False, 'message': 'Sessão não encontrada!'}), 400
            
            # Check if session is in progress
            if sessao[3] != 'A Decorrer':
                return jsonify({
                    'success': False, 
                    'message': 'Só é possível registar voltas em sessões com estado "A Decorrer"!'
                }), 400
            
            # Check weather conditions
            if sessao[0] is None or sessao[1] is None or sessao[2] is None:
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
        
        return jsonify({'success': True, 'message': 'Volta registada com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@tp_bp.route('/condicoes_pista')
def condicoes_pista():
    if 'loggedin' not in session:
        return redirect('/login')
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Verify user is Tecnico de Pista
        cursor.execute('SELECT * FROM Tecnico_de_Pista WHERE id_utilizador=?', (session['id'],))
        if cursor.fetchone() is None:
            return redirect('/logout')
        
        # Get active sessions (from events that are 'A Decorrer')
        cursor.execute("""
            SELECT s.id_sessao, s.data, s.tipo, s.hora_inicio, s.hora_fim,
                   s.temperatura_asfalto, s.temperatura_ar, s.humidade, s.precipitacao,
                   e.nome as evento_nome
            FROM Sessao s
            INNER JOIN Evento e ON s.id_evento = e.id_evento
            WHERE e.status = 'A Decorrer'
            ORDER BY s.data, s.hora_inicio
        """)
        
        sessoes_raw = cursor.fetchall()
    
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


@tp_bp.route('/api/sessao/<int:id>/condicoes', methods=['PUT'])
def atualizar_condicoes_sessao(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE Sessao 
                SET temperatura_asfalto=?, temperatura_ar=?, humidade=?, precipitacao=?
                WHERE id_sessao=?
            """, (
                data.get('temperatura_asfalto'),
                data.get('temperatura_ar'),
                data.get('humidade'),
                data.get('precipitacao'),
                id
            ))
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Condições atualizadas com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400
