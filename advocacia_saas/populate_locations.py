"""Script to populate database with Brazilian states and cities."""

from app import create_app, db
from app.models import Cidade, Estado

# Brazilian states
ESTADOS = [
    ("AC", "Acre"),
    ("AL", "Alagoas"),
    ("AP", "Amapá"),
    ("AM", "Amazonas"),
    ("BA", "Bahia"),
    ("CE", "Ceará"),
    ("DF", "Distrito Federal"),
    ("ES", "Espírito Santo"),
    ("GO", "Goiás"),
    ("MA", "Maranhão"),
    ("MT", "Mato Grosso"),
    ("MS", "Mato Grosso do Sul"),
    ("MG", "Minas Gerais"),
    ("PA", "Pará"),
    ("PB", "Paraíba"),
    ("PR", "Paraná"),
    ("PE", "Pernambuco"),
    ("PI", "Piauí"),
    ("RJ", "Rio de Janeiro"),
    ("RN", "Rio Grande do Norte"),
    ("RS", "Rio Grande do Sul"),
    ("RO", "Rondônia"),
    ("RR", "Roraima"),
    ("SC", "Santa Catarina"),
    ("SP", "São Paulo"),
    ("SE", "Sergipe"),
    ("TO", "Tocantins"),
]

# Main cities by state (sample data - you can expand this)
CIDADES = {
    "AC": ["Rio Branco", "Cruzeiro do Sul", "Sena Madureira", "Tarauacá", "Feijó"],
    "AL": ["Maceió", "Arapiraca", "Palmeira dos Índios", "Rio Largo", "Penedo"],
    "AP": ["Macapá", "Santana", "Laranjal do Jari", "Oiapoque", "Mazagão"],
    "AM": ["Manaus", "Parintins", "Itacoatiara", "Manacapuru", "Coari"],
    "BA": [
        "Salvador",
        "Feira de Santana",
        "Vitória da Conquista",
        "Camaçari",
        "Itabuna",
        "Juazeiro",
        "Lauro de Freitas",
        "Ilhéus",
    ],
    "CE": [
        "Fortaleza",
        "Caucaia",
        "Juazeiro do Norte",
        "Maracanaú",
        "Sobral",
        "Crato",
        "Itapipoca",
    ],
    "DF": ["Brasília"],
    "ES": [
        "Vitória",
        "Vila Velha",
        "Serra",
        "Cariacica",
        "Cachoeiro de Itapemirim",
        "Linhares",
        "Colatina",
    ],
    "GO": [
        "Goiânia",
        "Aparecida de Goiânia",
        "Anápolis",
        "Rio Verde",
        "Luziânia",
        "Águas Lindas de Goiás",
    ],
    "MA": ["São Luís", "Imperatriz", "São José de Ribamar", "Timon", "Caxias", "Codó"],
    "MT": [
        "Cuiabá",
        "Várzea Grande",
        "Rondonópolis",
        "Sinop",
        "Tangará da Serra",
        "Cáceres",
    ],
    "MS": [
        "Campo Grande",
        "Dourados",
        "Três Lagoas",
        "Corumbá",
        "Ponta Porã",
        "Aquidauana",
    ],
    "MG": [
        "Belo Horizonte",
        "Uberlândia",
        "Contagem",
        "Juiz de Fora",
        "Betim",
        "Montes Claros",
        "Ribeirão das Neves",
        "Uberaba",
        "Governador Valadares",
        "Ipatinga",
    ],
    "PA": [
        "Belém",
        "Ananindeua",
        "Santarém",
        "Marabá",
        "Castanhal",
        "Parauapebas",
        "Itaituba",
    ],
    "PB": ["João Pessoa", "Campina Grande", "Santa Rita", "Patos", "Bayeux", "Sousa"],
    "PR": [
        "Curitiba",
        "Londrina",
        "Maringá",
        "Ponta Grossa",
        "Cascavel",
        "São José dos Pinhais",
        "Foz do Iguaçu",
        "Colombo",
    ],
    "PE": [
        "Recife",
        "Jaboatão dos Guararapes",
        "Olinda",
        "Caruaru",
        "Petrolina",
        "Paulista",
        "Cabo de Santo Agostinho",
        "Camaragibe",
    ],
    "PI": ["Teresina", "Parnaíba", "Picos", "Piripiri", "Floriano", "Campo Maior"],
    "RJ": [
        "Rio de Janeiro",
        "São Gonçalo",
        "Duque de Caxias",
        "Nova Iguaçu",
        "Niterói",
        "Belford Roxo",
        "São João de Meriti",
        "Campos dos Goytacazes",
        "Petrópolis",
        "Volta Redonda",
    ],
    "RN": [
        "Natal",
        "Mossoró",
        "Parnamirim",
        "São Gonçalo do Amarante",
        "Macaíba",
        "Ceará-Mirim",
    ],
    "RS": [
        "Porto Alegre",
        "Caxias do Sul",
        "Pelotas",
        "Canoas",
        "Santa Maria",
        "Gravataí",
        "Viamão",
        "Novo Hamburgo",
        "São Leopoldo",
    ],
    "RO": ["Porto Velho", "Ji-Paraná", "Ariquemes", "Vilhena", "Cacoal", "Jaru"],
    "RR": ["Boa Vista", "Rorainópolis", "Caracaraí", "Alto Alegre", "Mucajaí"],
    "SC": [
        "Florianópolis",
        "Joinville",
        "Blumenau",
        "São José",
        "Criciúma",
        "Chapecó",
        "Itajaí",
        "Jaraguá do Sul",
        "Lages",
    ],
    "SP": [
        "São Paulo",
        "Guarulhos",
        "Campinas",
        "São Bernardo do Campo",
        "Santo André",
        "Osasco",
        "São José dos Campos",
        "Ribeirão Preto",
        "Sorocaba",
        "Santos",
        "Mauá",
        "São José do Rio Preto",
        "Mogi das Cruzes",
        "Diadema",
        "Piracicaba",
        "Carapicuíba",
        "Bauru",
        "Jundiaí",
        "Franca",
        "São Vicente",
    ],
    "SE": [
        "Aracaju",
        "Nossa Senhora do Socorro",
        "Lagarto",
        "Itabaiana",
        "Estância",
        "São Cristóvão",
    ],
    "TO": ["Palmas", "Araguaína", "Gurupi", "Porto Nacional", "Paraíso do Tocantins"],
}


def populate_estados_cidades():
    """Populate database with states and cities."""
    app = create_app()

    with app.app_context():
        print("Starting population of states and cities...")

        # Check if already populated
        if Estado.query.count() > 0:
            print("Database already contains states. Skipping...")
            return

        # Create states
        estados_dict = {}
        for sigla, nome in ESTADOS:
            estado = Estado(sigla=sigla, nome=nome)
            db.session.add(estado)
            estados_dict[sigla] = estado
            print(f"Added state: {sigla} - {nome}")

        db.session.flush()  # Get IDs

        # Create cities
        total_cities = 0
        for sigla, cidades in CIDADES.items():
            estado = estados_dict[sigla]
            for cidade_nome in cidades:
                cidade = Cidade(nome=cidade_nome, estado_id=estado.id)
                db.session.add(cidade)
                total_cities += 1
            print(f"Added {len(cidades)} cities for {sigla}")

        db.session.commit()
        print(f"\n✅ Successfully populated:")
        print(f"   - {len(ESTADOS)} states")
        print(f"   - {total_cities} cities")


if __name__ == "__main__":
    populate_estados_cidades()
