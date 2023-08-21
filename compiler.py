import ast
from ast import *
from utils import *
from x86_ast import *
import os
from typing import List, Tuple, Set, Dict

Binding = Tuple[Name, expr]
Temporaries = List[Binding]


class Compiler:

    ############################################################################
    # Remove Complex Operands
    ############################################################################

    # translation on the expr level
    def rco_exp(self, e: expr, need_atomic: bool) -> Tuple[expr, Temporaries]:
        """
        Make operands atomic.
        Return a pair consisting of the new expression and a list of pairs,
        associating new temporary variables with their initializing expressions.
        """
        match e:
            case Constant(_) | Name(_):
                return (e, [])
            case Call(Name('input_int'), []):
                if need_atomic:
                    tmp = Name(generate_name())
                    return (tmp, [(tmp, e)])
                else:
                    return (e, [])
            case UnaryOp(USub(), e):
                e_atomic, tmps = self.rco_exp(e, True)
                if need_atomic:
                    tmp = Name(generate_name())
                    tmps.append((tmp, UnaryOp(USub(), e_atomic)))
                    return (tmp, tmps)
                else:
                    return (UnaryOp(USub(), e_atomic), tmps)
            case BinOp(e1, op, e2):
               e1_atomic, tmps1 = self.rco_exp(e1, True) 
               e2_atomic, tmps2 = self.rco_exp(e2, True)
               if need_atomic:
                   tmp = Name(generate_name())
                   tmps = tmps1 + tmps2
                   tmps.append((tmp, BinOp(e1_atomic, op, e2_atomic)))
                   return (tmp, tmps)
               else:
                   tmps = tmps1 + tmps2
                   return (BinOp(e1_atomic, op, e2_atomic), tmps)
            case _:
                raise Exception('unhandled case')

    # translation on the stmt level
    def rco_stmt(self, s: stmt) -> List[stmt]:
        match s:
            case Expr(Call(Name('print'), [exp])):
                exp_atomic, tmps = self.rco_exp(exp, True)
                tmps_init = [Assign([tmp], init) for tmp, init in tmps]
                res = tmps_init
                res.append(Expr(Call(Name('print'), [exp_atomic])))
                return res
            case Expr(e):
                e_mon, tmps = self.rco_exp(e, False)
                tmps_init = [Assign([tmp], init) for tmp, init in tmps]
                res = tmps_init
                res.append(Expr(e_mon))
                return res
            case Assign([Name(var)], e):
                e_mon, tmps = self.rco_exp(e, False)
                tmps_init = [Assign([tmp], init) for tmp, init in tmps]
                res = tmps_init
                res.append(Assign([Name(var)], e_mon))
                return res
            case _:
                raise Exception('unhandled case')

    # translation on the module level
    def remove_complex_operands(self, p: Module) -> Module:
       match p:
           case Module(stmts):
                res = []
                for stmt in stmts:
                    res.extend(self.rco_stmt(stmt))
                return Module(res)
           case _:
               raise Exception('unhandled case')

    ############################################################################
    # Select Instructions
    ############################################################################

    def select_arg(self, e: expr) -> arg:
        # YOUR CODE HERE
        pass        

    def select_stmt(self, s: stmt) -> List[instr]:
        # YOUR CODE HERE
        pass        

    # def select_instructions(self, p: Module) -> X86Program:
    #     # YOUR CODE HERE
    #     pass        

    ############################################################################
    # Assign Homes
    ############################################################################

    def assign_homes_arg(self, a: arg, home: Dict[Variable, arg]) -> arg:
        # YOUR CODE HERE
        pass        

    def assign_homes_instr(self, i: instr,
                           home: Dict[Variable, arg]) -> instr:
        # YOUR CODE HERE
        pass        

    def assign_homes_instrs(self, ss: List[instr],
                            home: Dict[Variable, arg]) -> List[instr]:
        # YOUR CODE HERE
        pass        

    # def assign_homes(self, p: X86Program) -> X86Program:
    #     # YOUR CODE HERE
    #     pass        

    ############################################################################
    # Patch Instructions
    ############################################################################

    def patch_instr(self, i: instr) -> List[instr]:
        # YOUR CODE HERE
        pass        

    def patch_instrs(self, ss: List[instr]) -> List[instr]:
        # YOUR CODE HERE
        pass        

    # def patch_instructions(self, p: X86Program) -> X86Program:
    #     # YOUR CODE HERE
    #     pass        

    ############################################################################
    # Prelude & Conclusion
    ############################################################################

    # def prelude_and_conclusion(self, p: X86Program) -> X86Program:
    #     # YOUR CODE HERE
    #     pass        

