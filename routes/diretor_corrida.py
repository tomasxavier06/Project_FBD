# Rotas do Diretor de Corrida
from flask import Blueprint, render_template, request, jsonify, session, redirect
from utils.database import get_db_connection

dc_bp = Blueprint('diretor_corrida', __name__)


@dc_bp.route('/welcomeDC')
def welcomeDC():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Precisa fazer login para aceder a esta página!', 'redirect': '/login'}), 401
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Diretor_de_Corrida WHERE id_utilizador=?', (session['id'],))
    if cursor.fetchone() is None:
        conn.close()
        return redirect('/logout')
    conn.close()
    return render_template('WelcomeDC.html', username=session.get('username', 'Diretor'))


@dc_bp.route('/criar_evento', methods=['GET', 'POST'])
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


@dc_bp.route('/gerir_eventos')
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


@dc_bp.route('/eventos_passados')
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
@dc_bp.route('/api/evento/<int:id>', methods=['PUT'])
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


@dc_bp.route('/api/evento/<int:id>', methods=['DELETE'])
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


@dc_bp.route('/api/evento/<int:id>/status', methods=['PUT'])
def alterar_status_evento(id):
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE Evento SET status=? WHERE id_evento=?", (data['status'], id))
        
        # If event is concluded, also conclude all its sessions
        if data['status'] == 'Concluído':
            cursor.execute("UPDATE Sessao SET status='Concluída' WHERE id_evento=?", (id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Estado do evento atualizado!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@dc_bp.route('/api/evento/<int:id>', methods=['GET'])
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


@dc_bp.route('/api/evento/<int:id>/sessoes')
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


@dc_bp.route('/api/sessao/<int:id>/status', methods=['PUT'])
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


@dc_bp.route('/api/sessao', methods=['POST'])
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


@dc_bp.route('/api/sessao/<int:id>', methods=['PUT'])
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


@dc_bp.route('/api/sessao/<int:id>', methods=['DELETE'])
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
