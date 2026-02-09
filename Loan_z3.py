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

    solver = Solver()

    
    approved = Bool("approved")

    rate = Real("rate")
    
    age = RealVal(applicant.age)
    income = applicant.income
    score = applicant.credit_score
    months = applicant.months
    cosigner = BoolVal(applicant.cosigner)
    networth = applicant.networth
    requested = applicant.requested


    # implicazioni per l'età
    solver.add(Implies(age >= 75, Not(approved)))
    solver.add(Implies(age <= 18, Not(approved)))
    solver.add(Implies(And(age <= 25, Not(cosigner)), Not(approved)))


    # definiamo i tipi di lavoro, ogni richiedente può avere solo un tipo di lavoro
    is_permanent = Bool('is_permanent')
    is_temporary = Bool('is_temporary')
    is_unemployed = Bool('is_unemployed')

    solver.add(Or(is_permanent, is_temporary, is_unemployed))
    solver.add(Or(Not(is_permanent), Not(is_temporary)))
    solver.add(Or(Not(is_permanent), Not(is_unemployed)))
    solver.add(Or(Not(is_temporary), Not(is_unemployed)))

    solver.add(is_permanent == (applicant.work == 'permanent'))
    solver.add(is_temporary == (applicant.work == 'temporary'))
    solver.add(is_unemployed == (applicant.work == 'unemployed'))

    solver.add(Implies(Xor(is_unemployed,is_temporary), cosigner))
    solver.add(Implies(is_unemployed, (networth/requested) >= 1))


    # definiamo i tipi di prestito richiesto (al più uno per richiedente) e le condizioni
    is_personal = Bool('is_personal')
    is_car = Bool('is_car')
    is_house = Bool('is_house')

    solver.add(Or(is_personal, is_car, is_house))
    solver.add(Or(Not(is_personal), Not(is_car)))
    solver.add(Or(Not(is_personal), Not(is_house)))
    solver.add(Or(Not(is_car), Not(is_house)))

    solver.add(is_personal == (applicant.typeloan == 'personal'))
    solver.add(is_car == (applicant.typeloan == 'car'))
    solver.add(is_house == (applicant.typeloan == 'house'))

    solver.add(Implies(Xor(is_car,is_personal), applicant.requested <= 200000))
    solver.add(Implies(is_house, applicant.requested >= 30000))
    solver.add(Implies(is_car, age > 25))


    # definiamo requisito di patrimonio minimo per prestiti elevati
    solver.add(Implies(And(requested > 100000, Not(is_house)), 
                      networth >= 0.5 * requested), is_permanent)


    # vietiamo combinazioni rischiose
    solver.add(Implies(And(age > 65, is_house, months > 180), Not(approved)))
    solver.add(Implies(And(is_temporary, requested > 30000, Not(cosigner)), Not(approved)))
    solver.add(Implies(And(score < 600, income < 2500, Not(cosigner)), Not(approved)))


    # vincoli sulla durata in base all'età e al tipo
    solver.add(Implies(is_house, And(months >= 60, months <= 360)))
    solver.add(Implies(is_car, And(months >= 12, months <= 120)))
    solver.add(Implies(is_personal, months <= 180))

    solver.add(Implies(approved, age + (months/12) <= 85))


    # definiamo il tasso base secondo lo score (è giovane viene "penalizzato")
    base_rate = Real("base_rate")
    solver.add(Implies(age <= 35, base_rate == 1 + (1000 - score) * 0.007 + 0.2*Sqrt(35-age)))
    solver.add(Implies(age > 35, base_rate == 1 + (1000 - score) * 0.007))


    # abbassiamo il tasso per il mutuo
    type_adj = Real("type_adj")
    solver.add(And(
        Implies(is_house, type_adj == 0.0),
        Implies(Not(is_house), type_adj == 4.5)
    ))


    # aggiustiamo il tasso in base alla presenza di un cofirmatario
    cosigner_benefit = Real("cosigner_benefit")
    solver.add(And(
        Implies(And(cosigner, age <= 30), cosigner_benefit == -0.5),
        Implies(And(cosigner, age > 30), cosigner_benefit == -0.3),
        Implies(Not(cosigner), cosigner_benefit == 0.0)
    ))


    # aggiustiamo il tasso in base alle entrate
    income_adj = Real("income_adj")
    solver.add(And(
        Implies(income >= 4500, income_adj == 0.0),
        Implies(And(income >= 3500, income < 4500), income_adj == 0.05),
        Implies(And(income >= 2500, income < 3500), income_adj == 0.1),
        Implies(And(income >= 2000, income < 2500), income_adj == 0.15),
        Implies(income < 2000, income_adj == 0.2),
    ))


    # aggiustiamo il tasso in base alla richiesta e lo stipendio
    dti_adj = Real("dti_adj")
    solver.add(And(
        Implies(is_permanent, dti_adj == 0.5),
        Implies(is_temporary, dti_adj == 0.1 + requested/(income*months)),
        Implies(is_unemployed, dti_adj == requested/(income*months))
    ))


    # sommiamo le caratteristiche
    solver.add(rate == If(approved, base_rate + type_adj + cosigner_benefit + income_adj + dti_adj, 0))


    # rata mensile
    mp = applicant.requested / months + rate/100 * applicant.requested / 12
    
    solver.add(And(
        Implies(is_house, approved == (mp <= 0.5 * income)),
        Implies(Not(is_house), approved == (mp <= 0.2 * income))
    ))



    solver.add(Implies(applicant.blacklisted, Not(approved)))

    solver.add(approved)

    if solver.check() == sat:
        model = solver.model()

        print("APPROVATO")
        
        print(f"{applicant.name}")
        
        r = model.eval(rate)
        r_val = float(r.as_decimal(10).replace("?", ""))
            
        print(f"Tasso: {r_val:.2f}%")
        print(f"Reddito: €{applicant.income}")
        print(f"Importo: €{applicant.requested}")
        print(f"Credit score: {applicant.credit_score}")
            
        mp = model.eval(mp)
        mp_val = float(mp.as_decimal(10).replace("?", ""))
            
        print(f"Rata mensile ({months} mesi): €{mp_val:.2f}")
        interests = mp_val * months - applicant.requested
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



mario = Applicant(name="Mario",
                    age = 45,
                    work = 'permanent',
                    income = 3500,
                    networth = 1000,
                    credit_score = 850,
                    requested = 200000,
                    cosigner = False,
                    typeloan = 'house',
                    months = 360,
                    blacklisted = False)

loan_application(mario)