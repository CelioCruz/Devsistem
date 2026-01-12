from ..extensions import db
from datetime import datetime

class Ambiente(db.Model):
    __tablename__ = 'tb_ambiente'

    amb_id = db.Column(db.Integer, primary_key=True)
    amb_nome = db.Column(db.String(50), unique=True, nullable=False) 
    amb_descricao = db.Column(db.String(200), nullable=True)
    amb_ativo = db.Column(db.Boolean, default=True)
    amb_datcad = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relacionamento com Empresa (via tabela intermediária)
    empresas = db.relationship('Empresa', secondary='tb_empresa_tem_ambiente', lazy='subquery',
                               back_populates='ambientes_permitidos')

    def __repr__(self):
        return f'<Ambiente {self.amb_nome}>'