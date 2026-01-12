from flask_login import UserMixin
from ..extensions import db, login_manager
from datetime import datetime

class Usuario(UserMixin, db.Model):
    __tablename__ = 'tb_us'

    us_reg = db.Column(db.Integer, primary_key=True)
    us_cad = db.Column(db.String(100), nullable=False)
    us_email = db.Column(db.String(100), unique=True, nullable=False)
    us_senha = db.Column(db.String(200), nullable=False)
    us_ambiente_id = db.Column(db.Integer, db.ForeignKey('tb_ambiente.amb_id'), nullable=True)
    us_empresa_id = db.Column(db.Integer, db.ForeignKey('tb_empresa.emp_reg'), nullable=True)
    us_ativo = db.Column(db.Boolean, default=True)
    us_datcad = db.Column(db.DateTime, default=db.func.current_timestamp())
    loja_id = db.Column(db.String(2), default='01')

    # Novo campo: obriga o usuário a trocar a senha no próximo login
    us_forcar_troca_senha = db.Column(db.Boolean, default=False)

    # Relacionamentos
    ambiente = db.relationship('Ambiente', backref='usuarios')
    empresa = db.relationship('Empresa', back_populates='usuarios')

    def get_id(self):
        return str(self.us_reg)

@login_manager.user_loader
def load_user(user_id):
    if user_id == "-1":
        class ProgramadorMaster(UserMixin):
            # Identificação
            us_reg = -1
            us_cad = "cruzdevsoft"
            us_email = "master@system"
            us_tipo = "super_admin"
            us_ativo = True
            
            # Campos obrigatórios para compatibilidade
            us_ambiente_id = None      # acesso irrestrito
            us_empresa_id = 1          # ID da empresa padrão
            loja_id = '01'
            us_forcar_troca_senha = False

            # Relacionamentos simulados
            @property
            def ambiente(self):
                return None  # sem ambiente fixo
            
            @property
            def empresa(self):
                from .empresa import Empresa
                return Empresa.query.get(1)  # empresa padrão

            # Métodos exigidos
            def get_id(self):
                return "-1"

            # 👇 Adicione qualquer outro campo usado em templates/rotas
            # Ex: se usar current_user.nome, adicione:
            @property
            def nome(self):
                return "Super Admin"

        return ProgramadorMaster()
    else:
        try:
            return db.session.get(Usuario, int(user_id))
        except (ValueError, TypeError):
            return None