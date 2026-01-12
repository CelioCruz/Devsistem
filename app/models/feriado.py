from ..extensions import db
from datetime import datetime

class Feriado(db.Model):
    __tablename__ = 'tb_feriado'

    fer_reg = db.Column(db.Integer, primary_key=True)
    fer_descricao = db.Column(db.String(100), nullable=False)  # ex: 'Natal', 'Ano Novo'
    fer_data = db.Column(db.Date, nullable=False)  # data fixa ou móvel (armazenada como DATE)
    fer_tipo = db.Column(db.String(10), default='nacional')  # 'nacional', 'estadual', 'municipal'
    fer_ativo = db.Column(db.Boolean, default=True)
    fer_datcad = db.Column(db.DateTime, default=db.func.current_timestamp())

    fer_empresa_id = db.Column(db.Integer, db.ForeignKey('tb_empresa.emp_reg'), nullable=True)
    empresa = db.relationship('Empresa', back_populates='feriados')