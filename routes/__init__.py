# Pacote de rotas (Flask Blueprints)
from routes.auth import auth_bp
from routes.public import public_bp
from routes.diretor_corrida import dc_bp
from routes.diretor_equipa import de_bp
from routes.tecnico_pista import tp_bp


def register_blueprints(app):
    """Regista todos os blueprints na aplicação Flask."""
    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(dc_bp)
    app.register_blueprint(de_bp)
    app.register_blueprint(tp_bp)
