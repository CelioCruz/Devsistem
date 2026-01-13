from flask_login import UserMixin
from ..extensions import db, login_manager
from datetime import datetime

# 🔹 Tabela associativa N:N: DEFINIDA FORA DA CLASSE
usuario_ambiente = db.Table(
    'tb_usuario_ambiente',
    db.Column('usuario_id', db.Integer, db.ForeignKey('tb_us.us_reg'), primary_key=True),
    db.Column('ambiente_id', db.Integer, db.ForeignKey('tb_ambiente.amb_id'), primary_key=True)
)

class Usuario(UserMixin, db.Model):
    __tablename__ = 'tb_us'

    us_reg = db.Column(db.Integer, primary_key=True)
    us_cad = db.Column(db.String(100), nullable=False)
    us_email = db.Column(db.String(100), unique=True, nullable=False)
    us_senha = db.Column(db.String(200), nullable=False)
    
    # ⚠️ OPÇÃO 1: Manter o campo legado (opcional, para migração)
    # us_ambiente_id = db.Column(db.Integer, db.ForeignKey('tb_ambiente.amb_id'), nullable=True)
    
    # Recomendação: REMOVER us_ambiente_id se for usar só N:N
    # Mas se quiser manter por enquanto, comente a linha acima
    
    us_empresa_id = db.Column(db.Integer, db.ForeignKey('tb_empresa.emp_reg'), nullable=True)
    us_ativo = db.Column(db.Boolean, default=True)
    us_datcad = db.Column(db.DateTime, default=db.func.current_timestamp())
    loja_id = db.Column(db.String(2), default='01')
    us_forcar_troca_senha = db.Column(db.Boolean, default=False)

    # 🔹 Relacionamentos
    empresa = db.relationship('Empresa', back_populates='usuarios')
    
    # Relacionamento N:N com ambientes
    ambientes_permitidos = db.relationship(
        'Ambiente',
        secondary=usuario_ambiente,
        backref=db.backref('usuarios_autorizados', lazy='dynamic')
    )

    # ⚠️ Se mantiver us_ambiente_id, descomente esta linha:
    # ambiente = db.relationship('Ambiente', foreign_keys=[us_ambiente_id])

    def get_id(self):
        return str(self.us_reg)


@login_manager.user_loader
def load_user(user_id):
    if user_id == "-1":
        class ProgramadorMaster(UserMixin):
            us_reg = -1
            us_cad = "cruzdevsoft"
            us_email = "master@system"
            us_tipo = "super_admin"
            us_ativo = True
            us_empresa_id = 1
            loja_id = '01'
            us_forcar_troca_senha = False

            @property
            def empresa(self):
                from .empresa import Empresa
                return Empresa.query.get(1)

            @property
            def ambientes_permitidos(self):
                # Master tem acesso a todos → retorna lista vazia ou todos, dependendo da lógica
                # Na prática, nas rotas você ignora essa lista para master
                return []

            def get_id(self):
                return "-1"

            @property
            def nome(self):
                return "Super Admin"

        return ProgramadorMaster()
    else:
        try:
            return db.session.get(Usuario, int(user_id))
        except (ValueError, TypeError):
            return None