from z3 import *

class Applicant:
    def __init__(self, name, age, income, outstandingdebts,
                credit_score, requested,
                typeloan, months, blacklisted):
        self.name = name
        self.age = age
        self.income = income
        self.outstandingdebts = outstandingdebts
        self.credit_score = credit_score
        self.requested = requested
        self.typeloan = typeloan
        self.months = months
        self.blacklisted = blacklisted

def loan_application(applicant):
   
    solver = Solver()
    approved = Bool("approved")
    rate = Real("rate")
    monthly_payment = Real("monthly_payment")
    
    income = RealVal(applicant.income)
    score = applicant.credit_score
    months = applicant.months
 
    if applicant.blacklisted:
        solver.add(approved == False)
        solver.add(rate == 0)
        solver.add(monthly_payment == 0)

    else:

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

        solver.add(Implies(is_car, applicant.requested <= 50000))


        base_rate = Real("base_rate")
        solver.add(base_rate == (1000 - score) * 0.017)

        income_adj = Real("income_adj")
        solver.add(
            income_adj ==
            If(income >= 4500, -0.1,
            If(income >= 3500,  0.2,
            If(income >= 2500,  0.5,
            If(income >= 2000,  1.0,
                                 1.5))))
        )
        
        dti_adj = Real("dti_adj")
        solver.add(
            dti_adj ==
            If(applicant.requested <= 10000, -0.5,
            If(applicant.requested <= 25000,  0.0,
            If(applicant.requested <= 40000,  0.5,
                                              1.0)))
        )
        
        potential_rate = base_rate + income_adj + dti_adj
        solver.add(rate == If(approved, potential_rate, 0))

        solver.add(
            monthly_payment == If(approved, 
                                applicant.requested / months + rate/100 * applicant.requested / 12, 
                                0)
        )
        
        is_not_blacklisted = Not(BoolVal(applicant.blacklisted))
        score_ok = score >= 100
        rate_limit_ok = potential_rate <= 100.0
        income_min_ok = income >= 1000

        estimated_mp = applicant.requested / months + potential_rate/100 * applicant.requested / 12
        
        solver.add(
            approved == And(
            is_not_blacklisted,
            score_ok,
            rate_limit_ok,
            income_min_ok,
            If(is_house, 
                estimated_mp <= 0.5 * income,  
                estimated_mp <= 0.2 * income)
            )
        )

        solver.add(Implies(Not(approved), rate == 0))
    
    
    if solver.check() == sat:
        model = solver.model()
        is_approved = model.eval(approved)

        if is_true(is_approved):
            print("APPROVATO")
        
            print("\n" + "="*60)
            print(f"{applicant.name}")
            print("="*60)
        
            r = model.eval(rate)
            r_val = float(r.as_decimal(10).replace("?", ""))
            
            print("APPROVATO")
            print(f"Tasso: {r_val:.2f}%")
            print(f"Reddito: €{applicant.income}")
            print(f"Importo: €{applicant.requested}")
            print(f"Credit score: {applicant.credit_score}")
            
            mp = model.eval(monthly_payment)
            mp_val = float(mp.as_decimal(10).replace("?", ""))
            
            print(f"Rata mensile ({months} mesi): €{mp_val:.2f}")
            interests = mp_val *months - applicant.requested
            print(f"Interessi totali: €{interests:.2f}")
        else:
            print("RIFIUTATO")
            if applicant.blacklisted:
                print("Motivo: Cliente nella blacklist")
            elif applicant.credit_score < 100:
                print("Motivo: Credit score insufficiente")
            elif applicant.income < 1000:
                print("Motivo: Reddito insufficiente")
            else:
                print("Motivo: Tasso o sostenibilità non rispettati")


maria = Applicant(name="Maria",
                    age = 34,
                    income = 1500,
                    outstandingdebts = 553,
                    credit_score = 700,
                    requested = 5000,
                    typeloan='house',
                    months = 100,
                    blacklisted = False)
    
loan_application(maria)