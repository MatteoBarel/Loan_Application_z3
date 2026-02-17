from z3 import *

class Applicant:
    def __init__(self, name, age, work, income, networth,
                credit_score, requested, cosigner,
                typeloan, months, blacklisted):
        
        self.name = name
        self.age = age
        self.work = work
        self.income = income
        self.networth = networth
        self.credit_score = credit_score
        self.requested = requested
        self.cosigner = cosigner
        self.typeloan = typeloan
        self.months = months
        self.blacklisted = blacklisted



def loan_application(applicant):

    solver = Solver()                   # inizializzazione del solver

    approved = Bool("approved")         # variabile dell'approvazione che il solver in z3 deve determinare
    rate = Real("rate")                 # variabile per il tasso che il solver in z3 deve calcolare
    
    age = applicant.age
    cosigner = applicant.cosigner
    income = applicant.income
    score = applicant.credit_score
    months = applicant.months
    networth = applicant.networth
    requested = applicant.requested


    # definizione i tipi di lavoro: ogni richiedente può avere solo un tipo di lavoro
    is_permanent = Bool('is_permanent')
    is_temporary = Bool('is_temporary')
    is_unemployed = Bool('is_unemployed')

    solver.add(is_permanent == (applicant.work == 'permanent'))         # |   se e solo se
    solver.add(is_temporary == (applicant.work == 'temporary'))         # |   assegnamo T o F alle variabili
    solver.add(is_unemployed == (applicant.work == 'unemployed'))       # |   se e solo se

    solver.add(Or(is_permanent, is_temporary, is_unemployed))   # |   almeno deve essere vera
    solver.add(Or(Not(is_permanent), Not(is_temporary)))        # |   non possono essere vere entrambi
    solver.add(Or(Not(is_permanent), Not(is_unemployed)))       # |   non possono essere vere entrambi
    solver.add(Or(Not(is_temporary), Not(is_unemployed)))       # |   non possono essere vere entrambi


    # definiamo i tipi di prestito richiesto (al più uno per richiedente) e le condizioni
    is_personal = Bool('is_personal')
    is_car = Bool('is_car')
    is_house = Bool('is_house')

    solver.add(is_personal == (applicant.typeloan == 'personal'))       # |
    solver.add(is_car == (applicant.typeloan == 'car'))                 # |   assegnazione T o F alle variabili
    solver.add(is_house == (applicant.typeloan == 'house'))             # |

    solver.add(Or(is_personal, is_car, is_house))           # |   almeno una deve essere vera
    solver.add(Or(Not(is_personal), Not(is_car)))           # |   non possono essere vere entrambi
    solver.add(Or(Not(is_personal), Not(is_house)))         # |   non possono essere vere entrambi
    solver.add(Or(Not(is_car), Not(is_house)))              # |   non possono essere vere entrambi


    # implicazioni per l'età
    solver.add(Implies(age >= 75, Not(approved)))
    solver.add(Implies(age <= 18, Not(approved)))
    solver.add(Implies(And(age <= 25, Not(cosigner)), Not(approved)))


    # implicazioni per il tipo di lavoro
    solver.add(Implies(Xor(is_unemployed,is_temporary), cosigner))
    solver.add(Implies(And(is_unemployed,Not(cosigner)), (networth >= requested)))


    # 
    solver.add(Implies(Xor(is_car,is_personal), applicant.requested <= 200000))     
    solver.add(Implies(is_house, applicant.requested >= 30000))
    solver.add(Implies(is_car, age > 25))


    # definiamo requisito di patrimonio minimo per prestiti elevati
    solver.add(Implies(And(requested > 100000, Not(is_house),               
                      networth >= 0.5 * requested), is_permanent))


    # vietiamo combinazioni rischiose
    solver.add(Implies(And(age > 65, is_house, months > 180), Not(approved)))
    solver.add(Implies(And(is_temporary, requested > 30000, Not(cosigner)), Not(approved)))
    solver.add(Implies(And(score < 600, income < 2500, Not(cosigner)), Not(approved)))


    # vincoli sulla durata in base all'età e al tipo
    solver.add(Implies(is_house, And(months >= 60, months <= 360)))
    solver.add(Implies(is_car, And(months >= 12, months <= 120)))
    solver.add(Implies(is_personal, months <= 180))

    solver.add(Implies(approved, age + (months/12) <= 85))


    # definizione del tasso base secondo lo score (è giovane viene "penalizzato")
    base_rate = Real("base_rate")
    solver.add(score <= 1000)
    solver.add(Implies(age <= 35, base_rate == 1 + (1000 - score) * 0.007 + 0.2*Sqrt(35-age)))
    solver.add(Implies(age > 35, base_rate == 1 + (1000 - score) * 0.007))


    # tasso per il mutuo o meno
    type_adj = Real("type_adj")
    solver.add(And(
        Implies(is_house, type_adj == 0.0),
        Implies(Not(is_house), type_adj == 4.5)
    ))


    # tasso in base alla presenza di un cofirmatario
    cosigner_benefit = Real("cosigner_benefit")
    solver.add(And(
        Implies(And(cosigner, age <= 30), cosigner_benefit == -0.5),
        Implies(And(cosigner, age > 30), cosigner_benefit == -0.3),
        Implies(Not(cosigner), cosigner_benefit == 0.0)
    ))


    # tasso in base alle entrate
    income_adj = Real("income_adj")
    solver.add(And(
        Implies(income >= 4500, income_adj == 0.0),
        Implies(And(income >= 3500, income < 4500), income_adj == 0.05),
        Implies(And(income >= 2500, income < 3500), income_adj == 0.1),
        Implies(And(income >= 2000, income < 2500), income_adj == 0.15),
        Implies(income < 2000, income_adj == 0.2),
    ))


    # tasso in base alla richiesta e lo stipendio
    dti_adj = Real("dti_adj")
    solver.add(And(
        Implies(is_permanent, dti_adj == 0.0),
        Implies(is_temporary, dti_adj == requested/(income*months)),
        Implies(is_unemployed, dti_adj == 1)
    ))


    # somma delle caratteristiche
    solver.add(rate ==  base_rate + type_adj + cosigner_benefit + income_adj + dti_adj)


    # rata mensile
    mp = requested / months + rate/100 * requested / 12
    
    solver.add(And(
        Implies(is_house, approved == (mp <= 0.5 * income)),
        Implies(Not(is_house), approved == (mp <= 0.2 * income))
    ))


    # controllo blacklist
    solver.add(Implies(applicant.blacklisted, Not(approved)))

    # approve deve essere True
    solver.add(approved)

    if solver.check() == sat:    # verifica che esista una soluzione
        model = solver.model()   # se è sat il modello restituisce i valori approved e rate

        print("APPROVATO:")
        print(f"{applicant.name}\n")
        
        # estrazione del valore del tasso, con conversione da valore di z3 a python
        r = model.eval(rate)                  
        r_val = float(r.as_decimal(10).replace("?", ""))
        
        # estrazione del valore della rata mensile, con conversione da valore di z3 a python
        mp = model.eval(mp)
        mp_val = float(mp.as_decimal(10).replace("?", ""))
            
        total_interests = mp_val * months - requested

        return {
            'approved': True,
            'rate': r_val,
            'monthly_payment': mp_val,
            'total_interests': total_interests,
            'total_due': total_interests + requested
        }
    
    else:
        print("NON APPROVATO:")
        print(f"{applicant.name}\n")
        return None


def portfolio_decision_problem(applicants, budget, target_profit):

    solver = Solver()       # inizializzazione del solver

    # risultati per ogni richiedente e salvati nella lista
    loan_results = []
    for i, app in enumerate(applicants):
        result = loan_application(app)
        loan_results.append(result)

    n = len(applicants)
    
    # creazione delle variabili per riconoscere la selezionabilità del richiedente
    selected = []
    for i in range(n):
        selected.append(Bool(f"select_{i}"))
    
    # creazione delle variabili per il costo di ogni prestito
    costs = []
    for i in range(n):
        costs.append(Real(f"cost_{i}"))

    # creazione delle variabili per il profitto di ogni prestito
    profits = []
    for i in range(n):
        profits.append(Real(f"profit_{i}"))
    
    for i in range(n):
        # se non è approvabile si setta tutto a 0
        if loan_results[i] is None:                     
            solver.add(Not(selected[i]))
            solver.add(costs[i] == 0)
            solver.add(profits[i] == 0)
        else:
            # se selezionato il costo sarà = alla richiesta del prestito, altrimenti 0
            solver.add(Implies(selected[i], costs[i] == applicants[i].requested))
            solver.add(Implies(Not(selected[i]), costs[i] == 0))
            # se selezionato il profitto sarà = al profitto del prestito, altrimenti 0
            solver.add(Implies(selected[i], profits[i] == loan_results[i]['total_interests']))
            solver.add(Implies(Not(selected[i]), profits[i] == 0))
    
    # il capitale prestato deve essere inferiore al budget
    total_cost = Sum(costs)
    solver.add(total_cost <= budget)
    
    # il profitto deve superare la soglia target
    total_profit = Sum(profits)
    solver.add(total_profit >= target_profit)
    

    if solver.check() == sat:   # verifica che esista una soluzione
        model = solver.model()  # se è sat il modello restituisce i selezionati
        
        total_investment = 0
        total_profit_actual = 0
        count = 0
        
        print(f"SELEZIONATI:")

        for i in range(n):
            if model.eval(selected[i]):
                app = applicants[i]
                result = loan_results[i]
                
                count += 1
                total_investment += app.requested
                total_profit_actual += result['total_interests']
                
                print(f"{app.name}")
                print(f"   Importo: €{app.requested:,.2f}")
                print(f"   Tasso: {result['rate']:.2f}%")
                print(f"   Profitto: €{result['total_interests']:,.2f}\n")
        
        print(f"Capitale investito: €{total_investment:,.2f} <= €{budget:,.2f}")
        print(f"Profitto totale: €{total_profit_actual:,.2f} >= €{target_profit:,.2f}")

        return True
    
    else:
        print("Nessuna soluzione possibile")
        return False
    

applicants = [
    Applicant(name="Mario",
                age=40, work='permanent', income=1500, networth=80000,
                credit_score=750, requested=50000, cosigner=False,
                typeloan='house', months=180, blacklisted=False),
    
    Applicant(name="Luigi",
                age=30, work='permanent', income=4000, networth=50000,
                credit_score=800, requested=30000, cosigner=False,
                typeloan='car', months=60, blacklisted=True),
    
    Applicant(name="Anna",
                age=35, work = 'permanent', income=1800, networth=20000,
                credit_score=780, requested=30000, cosigner=True,
                typeloan='personal', months=180, blacklisted=False),

    Applicant(name="Anna",
            age=35, work = 'permanent', income=1800, networth=20000,
            credit_score=780, requested=30000, cosigner=True,
            typeloan='personal', months=180, blacklisted=False),

    Applicant(name="Anna",
                age=35, work = 'permanent', income=1800, networth=20000,
                credit_score=780, requested=30000, cosigner=True,
                typeloan='personal', months=180, blacklisted=False),
                
    Applicant(name="Anna",
                age=35, work = 'permanent', income=1800, networth=20000,
                credit_score=780, requested=30000, cosigner=True,
                typeloan='personal', months=180, blacklisted=False),

]

solution_exists = portfolio_decision_problem(
    applicants, 
    budget = 120000, 
    target_profit = 50000
)