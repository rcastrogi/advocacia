#!/usr/bin/env bash#!/usr/bin/env bash

# Script de build para Render.com# Script de build para o Render.com



set -o errexit# Instalar dependências

pip install -r requirements.txt

echo "🔧 Instalando dependências..."

pip install -r requirements.txt# Executar migrações do banco de dados

python << END

echo "🗄️  Inicializando banco de dados..."from app import create_app, db

python << ENDfrom app.models import User

from app import create_app, dbfrom app.models.location import Estado, Cidade

from app.models import User

app = create_app()

app = create_app()

with app.app_context():

with app.app_context():    # Criar todas as tabelas

    # Criar tabelas    db.create_all()

    db.create_all()    print("✅ Tabelas criadas!")

    print("✅ Tabelas criadas!")    

        # Criar usuário admin se não existir

    # Criar usuário admin se não existir    if User.query.count() == 0:

    admin = User.query.filter_by(email="admin@advocaciasaas.com").first()        admin = User(

    if not admin:            username='admin',

        admin = User(            email='admin@petitio.com',

            username="admin",            is_master=True

            email="admin@advocaciasaas.com",        )

            full_name="Administrador do Sistema",        admin.set_password('admin123')

            user_type="master",        db.session.add(admin)

            oab_number="123456"        db.session.commit()

        )        print("✅ Usuário admin criado!")

        admin.set_password("admin123")    

        db.session.add(admin)    # Popular estados e cidades se não existirem

        db.session.commit()    if Estado.query.count() == 0:

        print("✅ Usuário admin criado!")        print("📍 Populando estados e cidades...")

        print("📧 Email: admin@advocaciasaas.com")        

        print("🔑 Senha: admin123")        ESTADOS = [

    else:            {'sigla': 'AC', 'nome': 'Acre'},

        print("✅ Usuário admin já existe!")            {'sigla': 'AL', 'nome': 'Alagoas'},

END            {'sigla': 'AP', 'nome': 'Amapá'},

            {'sigla': 'AM', 'nome': 'Amazonas'},

echo "✅ Build concluído com sucesso!"            {'sigla': 'BA', 'nome': 'Bahia'},

            {'sigla': 'CE', 'nome': 'Ceará'},
            {'sigla': 'DF', 'nome': 'Distrito Federal'},
            {'sigla': 'ES', 'nome': 'Espírito Santo'},
            {'sigla': 'GO', 'nome': 'Goiás'},
            {'sigla': 'MA', 'nome': 'Maranhão'},
            {'sigla': 'MT', 'nome': 'Mato Grosso'},
            {'sigla': 'MS', 'nome': 'Mato Grosso do Sul'},
            {'sigla': 'MG', 'nome': 'Minas Gerais'},
            {'sigla': 'PA', 'nome': 'Pará'},
            {'sigla': 'PB', 'nome': 'Paraíba'},
            {'sigla': 'PR', 'nome': 'Paraná'},
            {'sigla': 'PE', 'nome': 'Pernambuco'},
            {'sigla': 'PI', 'nome': 'Piauí'},
            {'sigla': 'RJ', 'nome': 'Rio de Janeiro'},
            {'sigla': 'RN', 'nome': 'Rio Grande do Norte'},
            {'sigla': 'RS', 'nome': 'Rio Grande do Sul'},
            {'sigla': 'RO', 'nome': 'Rondônia'},
            {'sigla': 'RR', 'nome': 'Roraima'},
            {'sigla': 'SC', 'nome': 'Santa Catarina'},
            {'sigla': 'SP', 'nome': 'São Paulo'},
            {'sigla': 'SE', 'nome': 'Sergipe'},
            {'sigla': 'TO', 'nome': 'Tocantins'}
        ]
        
        # Principais cidades do Brasil
        CIDADES = {
            'SP': ['São Paulo', 'Campinas', 'Santos', 'Ribeirão Preto', 'Sorocaba'],
            'RJ': ['Rio de Janeiro', 'Niterói', 'Duque de Caxias', 'Nova Iguaçu', 'Petrópolis'],
            'MG': ['Belo Horizonte', 'Uberlândia', 'Contagem', 'Juiz de Fora', 'Betim'],
            'BA': ['Salvador', 'Feira de Santana', 'Vitória da Conquista', 'Camaçari', 'Ilhéus'],
            'PR': ['Curitiba', 'Londrina', 'Maringá', 'Ponta Grossa', 'Cascavel'],
            'RS': ['Porto Alegre', 'Caxias do Sul', 'Pelotas', 'Canoas', 'Santa Maria'],
            'PE': ['Recife', 'Jaboatão dos Guararapes', 'Olinda', 'Caruaru', 'Petrolina'],
            'CE': ['Fortaleza', 'Caucaia', 'Juazeiro do Norte', 'Maracanaú', 'Sobral'],
            'SC': ['Florianópolis', 'Joinville', 'Blumenau', 'Chapecó', 'Criciúma'],
            'GO': ['Goiânia', 'Aparecida de Goiânia', 'Anápolis', 'Rio Verde', 'Luziânia'],
            'AM': ['Manaus', 'Parintins', 'Itacoatiara', 'Manacapuru', 'Coari'],
            'ES': ['Vitória', 'Vila Velha', 'Serra', 'Cariacica', 'Linhares'],
            'PA': ['Belém', 'Ananindeua', 'Santarém', 'Marabá', 'Castanhal'],
            'DF': ['Brasília'],
            'MA': ['São Luís', 'Imperatriz', 'Caxias', 'Timon', 'Codó'],
            'MT': ['Cuiabá', 'Várzea Grande', 'Rondonópolis', 'Sinop', 'Tangará da Serra'],
            'MS': ['Campo Grande', 'Dourados', 'Três Lagoas', 'Corumbá', 'Ponta Porã'],
            'PB': ['João Pessoa', 'Campina Grande', 'Santa Rita', 'Patos', 'Bayeux'],
            'RN': ['Natal', 'Mossoró', 'Parnamirim', 'São Gonçalo do Amarante', 'Macaíba'],
            'AL': ['Maceió', 'Arapiraca', 'Rio Largo', 'Palmeira dos Índios', 'União dos Palmares'],
            'SE': ['Aracaju', 'Nossa Senhora do Socorro', 'Lagarto', 'Itabaiana', 'Estância'],
            'RO': ['Porto Velho', 'Ji-Paraná', 'Ariquemes', 'Vilhena', 'Cacoal'],
            'TO': ['Palmas', 'Araguaína', 'Gurupi', 'Porto Nacional', 'Paraíso do Tocantins'],
            'AC': ['Rio Branco', 'Cruzeiro do Sul', 'Sena Madureira', 'Tarauacá', 'Feijó'],
            'AP': ['Macapá', 'Santana', 'Laranjal do Jari', 'Oiapoque', 'Mazagão'],
            'RR': ['Boa Vista', 'Rorainópolis', 'Caracaraí', 'Alto Alegre', 'Mucajaí'],
            'PI': ['Teresina', 'Parnaíba', 'Picos', 'Floriano', 'Piripiri']
        }
        
        for estado_data in ESTADOS:
            estado = Estado(sigla=estado_data['sigla'], nome=estado_data['nome'])
            db.session.add(estado)
            db.session.flush()
            
            if estado_data['sigla'] in CIDADES:
                for cidade_nome in CIDADES[estado_data['sigla']]:
                    cidade = Cidade(nome=cidade_nome, estado_id=estado.id)
                    db.session.add(cidade)
        
        db.session.commit()
        print(f"✅ {Estado.query.count()} estados e {Cidade.query.count()} cidades criados!")
    
    print("🎉 Banco de dados inicializado com sucesso!")
END
