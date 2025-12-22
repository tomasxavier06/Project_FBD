from flask import Blueprint, render_template, request, jsonify
from utils.database import get_db

public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def homepage():
    return render_template('homepage.html')


@public_bp.route('/pilots')
def pilots():
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            pesquisa = request.args.get('nome_procurado')
            coluna = request.args.get('coluna', 'nome')
            ordem = request.args.get('ordem', 'asc')

            colunas_validas = ['numero_licenca', 'nome', 'data_nascimento', 'nacionalidade', 'nome_equipa', 'numero_eventos']

            if coluna not in colunas_validas:
                coluna = 'nome'

            if ordem.lower() not in ['asc', 'desc']:
                ordem = 'asc'

            query = "SELECT numero_licenca, nome, data_nascimento, nacionalidade, nome_equipa, numero_eventos, idade FROM vw_RankingPilotos"
            parametros = []

            if pesquisa:
                query += " WHERE (nome LIKE ? OR nome_equipa LIKE ? OR nacionalidade LIKE ?)"
                parametros.append(f"%{pesquisa}%")
                parametros.append(f"%{pesquisa}%")
                parametros.append(f"%{pesquisa}%")

                        
            query += f" ORDER BY {coluna} {ordem}"
            
            cursor.execute(query, tuple(parametros))
            pilotos = cursor.fetchall()
            
        return render_template('pilots.html', pilotos=pilotos, ordem_atual=ordem, coluna_ativa=coluna, pesquisa_feita=pesquisa)
    except Exception as e:
        print(f"erro real: {e}")
        return "<h3>Não foi possível carregar os pilotos. Tente novamente</h3>"


@public_bp.route('/teams')
def teams():
    try:
        with get_db() as conn:
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
            
        return render_template('teams.html', equipas=equipas_lista, ordem_atual=ordem, coluna_ativa=coluna, pesquisa_feita=pesquisa)
    except Exception as e:
        print(f"erro real: {e}")
        return "<h3>Não foi possível carregar as equipas. Tente novamente</h3>"


@public_bp.route('/team/<int:id>')
def team_details(id):
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT nome, pais FROM Equipa WHERE id_equipa = ?", (id,))
            equipa = cursor.fetchone()

            if not equipa:
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

        return render_template('team_details.html', equipa=equipa, pilotos=pilotos, carros=carros)
    except Exception as e:
        print(f"Erro ao carregar detalhes da equipa: {e}")
        return "<h3>Erro ao carregar detalhes.</h3>"


@public_bp.route('/events')
def events():
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            pesquisa = request.args.get('nome_procurado', '')
            
            cursor.execute("EXEC sp_ManutencaoStatusEventos")
            conn.commit()
            
            if pesquisa:
                query = """
                    SELECT 
                        E.id_evento, E.nome, E.tipo, E.data_inicio, E.data_fim, E.status,
                        (SELECT COUNT(DISTINCT id_equipa) FROM Participa_Evento PE WHERE PE.id_evento = E.id_evento) as total_equipas,
                        (SELECT COUNT(DISTINCT ps.numero_licenca) 
                        FROM Participa_Sessao ps 
                        JOIN Sessao s ON ps.id_sessao = s.id_sessao 
                        WHERE s.id_evento = E.id_evento) as total_pilotos
                    FROM Evento E
                    WHERE E.nome LIKE ? OR E.tipo LIKE ? OR E.status LIKE ?
                    ORDER BY E.data_inicio DESC
                """
                v = f"%{pesquisa}%"
                cursor.execute(query, (v, v, v))
            else:
                cursor.execute("EXEC sp_ListarEventosComTotais")
            
            eventos = cursor.fetchall()
        
        return render_template('events.html', eventos=eventos, pesquisa_feita=pesquisa)
    except Exception as e:
        print(f"Erro na rota de eventos: {e}")
        return f"Erro: {e}"


@public_bp.route('/api/lap_details/<int:id_volta>')
def lap_details(id_volta):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # query que junta a Volta com a Sessão para obter os dados técnicos
            query = """
                SELECT 
                    S.temperatura_asfalto, S.temperatura_ar, S.humidade, S.precipitacao,
                    V.pressao_pneus, V.numero_volta, S.tipo as tipo_sessao,
                    dbo.fn_FormatarTempoMS(V.tempo) as tempo
                FROM Volta V
                INNER JOIN Sessao S ON V.id_sessao = S.id_sessao
                WHERE V.id_volta = ?
            """
            cursor.execute(query, (id_volta,))
            row = cursor.fetchone()

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


@public_bp.route('/records')
def records():
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT DISTINCT nome FROM Piloto ORDER BY nome")
            lista_pilotos = [row[0] for row in cursor.fetchall()]

            cursor.execute("""
                SELECT DISTINCT (marca + ' ' + modelo) 
                FROM Carro 
                ORDER BY (marca + ' ' + modelo)
            """)
            lista_carros = [row[0] for row in cursor.fetchall()]

            cursor.execute("SELECT DISTINCT nome FROM Evento ORDER BY nome")
            lista_eventos = [row[0] for row in cursor.fetchall()]

            f_piloto = request.args.get('piloto', '')
            f_carro = request.args.get('carro', '')
            f_evento = request.args.get('evento', '')

            query = "SELECT tempo_formatado, piloto, carro, evento, tempo, data, id_volta, gap FROM vw_Recordes WHERE 1=1"
            params = []

            if f_piloto:
                query += " AND piloto = ?"
                params.append(f_piloto)
            if f_carro:
                query += " AND carro = ?"
                params.append(f_carro)
            if f_evento:
                query += " AND evento = ?"
                params.append(f_evento)

            query += " ORDER BY tempo ASC"

            cursor.execute(query, params)
            recordes = cursor.fetchall()

        return render_template('records.html', 
                               recordes=recordes,
                               lista_pilotos=lista_pilotos,
                               lista_carros=lista_carros,
                               lista_eventos=lista_eventos,
                               f_piloto=f_piloto,
                               f_carro=f_carro,
                               f_evento=f_evento)
    except Exception as e:
        print(f"Erro detalhado nos recordes: {e}")
        return f"<h3>Erro ao carregar a página de recordes: {e}</h3>"
