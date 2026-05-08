from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func

app = Flask(__name__)

# Conexão com o banco MySQL
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://rooroot@localhost/anomalias"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class Event(db.Model):
    __tablename__ = "eventos"

    id = db.Column(db.Integer, primary_key=True)
    hora = db.Column(db.DateTime, nullable=False)
    categoria = db.Column(db.String(100), nullable=False)
    severidade = db.Column(db.String(50), nullable=False)
    origem = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=True)


def resumo_severidade():
    rows = (
        db.session.query(Event.severidade, func.count(Event.id))
        .group_by(Event.severidade)
        .all()
    )

    mapa = {sev: qtd for sev, qtd in rows}

    return {
        "critico": mapa.get("Crítico", 0),
        "alto": mapa.get("Alto", 0),
        "moderado": mapa.get("Moderado", 0),
    }


@app.route("/")
def dashboard():
    total = Event.query.count()
    eventos = Event.query.order_by(Event.hora.desc()).limit(10).all()
    sev = resumo_severidade()
    ultima_atualizacao = datetime.now()

    return render_template(
        "dashboard.html",
        total=total,
        eventos=eventos,
        sev=sev,
        ultima_atualizacao=ultima_atualizacao
    )


@app.route("/api/events")
def api_events():
    eventos = Event.query.order_by(Event.hora.desc()).limit(10).all()

    return jsonify([
        {
            "hora": e.hora.strftime("%d/%m/%Y %H:%M"),
            "categoria": e.categoria,
            "severidade": e.severidade,
            "origem": e.origem
        } for e in eventos
    ])


@app.route("/api/summary")
def api_summary():
    return jsonify({
        "total": Event.query.count(),
        "sev": resumo_severidade(),
        "ultima_atualizacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    })


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)