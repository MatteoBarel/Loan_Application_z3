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
        Implies(is_unemployed, dti_adj == 0.2 + requested/(income*months))
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

        print("APPROVATO")
        
        print(f"{applicant.name}")
        
        # estrazione del valore del tasso, con conversione da valore di z3 a python
        r = model.eval(rate)                  
        r_val = float(r.as_decimal(10).replace("?", ""))
            
        print(f"Tasso: {r_val:.2f}%")
        print(f"Reddito: €{income}")
        print(f"Importo: €{requested}")
        print(f"Credit score: {applicant.credit_score}")
        
        # estrazione del valore della rata mensile, con conversione da valore di z3 a python
        mp = model.eval(mp)
        mp_val = float(mp.as_decimal(10).replace("?", ""))
            
        print(f"Rata mensile ({months} mesi): €{mp_val:.2f}")
        interests = mp_val * months - requested
        print(f"Interessi totali: €{interests:.2f}")
        print(f"Totale dovuto: €{(interests+requested):.2f}")

    else:
        print('\n')
        print("RIFIUTATO")
        print(f"{applicant.name}")
        if applicant.blacklisted:
            print("Motivo: Cliente nella blacklist")
        elif applicant.age > 75:
            print("Motivo: Età non conforme")
        elif applicant.age <= 25 and applicant.cosigner == False:
            print("Motivo: mancanza di un co-firmatario")
        elif applicant.credit_score < 100:
            print("Motivo: Credit score insufficiente")
        elif applicant.income < 1000:
            print("Motivo: Reddito insufficiente")
        else:
            print("Motivo: Tasso o sostenibilità non rispettati")


# dati del candidato

mario = Applicant(name="Mario",
                    age = 40,
                    work = 'temporary',
                    income = 1500,
                    networth = 100000,
                    credit_score = 850,
                    requested = 60000,
                    cosigner = True,
                    typeloan = 'house',
                    months = 240,
                    blacklisted = False)

loan_application(mario)