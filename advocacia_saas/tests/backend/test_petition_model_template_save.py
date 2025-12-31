import pytest
from app import create_app


def test_petition_model_template_save(tmp_path, monkeypatch):
    app = create_app({"TESTING": True})
    with app.app_context():
        from app.models import PetitionModel, db

        # Criar modelo de teste
        model = PetitionModel(name="Test Model", slug="test-model", petition_type_id=1)
        db.session.add(model)
        db.session.commit()

        # Simular salvar template
        model.template_content = "{{ FIELD }}"
        db.session.commit()

        m = PetitionModel.query.get(model.id)
        assert m.template_content == "{{ FIELD }}"
