from ..extensions import db
from datetime import datetime

class Vendedor(db.Model):
    __tablename__ = 'tb_vendedor'
    vend_reg = db.Column(db.Integer, primary_key=True)
    vend_codigo = db.Column(db.String(4), unique=True, nullable=False)
    vend_nome = db.Column(db.String(150), nullable=False)
    vend_empresa = db.Column(db.String(100), nullable=False)
    vend_ativo = db.Column(db.Boolean, default=True)
    vend_datcad = db.Column(db.DateTime, default=db.func.current_timestamp())

    @staticmethod
    def gerar_codigo():
        ultimo = db.session.query(db.func.max(Vendedor.vend_reg)).scalar()
        proximo = (ultimo or 0) + 1
        return f"{proximo:04d}"