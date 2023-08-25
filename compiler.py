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
        match e:
            case Constant(n):
                return Immediate(n)
            case Name(var):
                return Variable(var)
            case _:
                raise Exception('invalid input')

    def select_stmt(self, s: stmt) -> List[instr]:
        match s:
            case Expr(Call(Name('print'), [a_exp])):
                arg = self.select_arg(a_exp)
                return [
                    Instr('movq', [arg, Reg('rdi')]),
                    Callq(label_name('print_int'), 1)
                ]
            case Expr(exp):
                match exp:
                    case Call(Name('input_int'), []):
                        return [
                            Callq(label_name('read_int'), 0)
                        ]
                    case _:
                        return []
            case Assign([Name(lhs)], exp):
                match exp:
                    case Constant(n):
                        return [
                            Instr('movq', [Immediate(n), Variable(lhs)])
                        ]
                    case Name(rhs):
                        return [
                            Instr('movq', [Variable(rhs), Variable(lhs)])
                        ]
                    case Call(Name('input_int'), []):
                        return [
                            Callq(label_name('read_int'), 0),
                            Instr('movq', [Reg('rax'), Variable(lhs)])
                        ]
                    case UnaryOp(USub(), Name(arg)) if lhs == arg:
                        return [
                            Instr('negq', [Variable(lhs)])
                        ]
                    case UnaryOp(USub(), a):
                        return [
                            Instr('movq', [self.select_arg(a), Variable(lhs)]),
                            Instr('negq', [Variable(lhs)])
                        ]
                    case BinOp(Name(arg1), Add(), atm2) if lhs == arg1:
                        return [
                            Instr('addq', self.select_arg(atm2), Variable(lhs))
                        ]
                    case BinOp(atm1, Add(), Name(arg2)) if lhs == arg2:
                        return [
                            Instr('addq', self.select_arg(atm1), Variable(arg2))
                        ]
                    case BinOp(atm1, Add(), atm2):
                        return [
                            Instr('movq', [self.select_arg(atm2), Variable(lhs)]),
                            Instr('addq', [self.select_arg(atm1), Variable(lhs)])
                        ]
                    case BinOp(Name(atm1), Sub(), atm2) if lhs == atm1:
                        return [
                            Instr('subq', self.select_arg(atm2), Variable(lhs))
                        ]
                    case BinOp(atm1, Sub(), atm2):
                        return [
                            Instr('movq', [self.select_arg(atm1), Variable(lhs)]),
                            Instr('subq', [self.select_arg(atm2), Variable(lhs)])
                        ]
                    case _:
                        raise Exception('unhandled case')

    def select_instructions(self, p: Module) -> X86Program:
        match p:
            case Module(stmts):
                instrs = []
                for stmt in stmts:
                    instrs.extend(self.select_stmt(stmt))
                return X86Program(instrs)

    ############################################################################
    # Assign Homes
    ############################################################################

    def assign_homes_arg(self, a: arg, home: Dict[Variable, arg]) -> arg:
        match a:
            case Immediate(_) | Reg(_) | Deref(_, _):
                return a
            case Variable(_):
                if a in home:
                    return home[a]
                else:
                    assigned_home = Deref('rbp', - len(home) * 8)
                    home[a] = assigned_home
                    return assigned_home

    def assign_homes_instr(self, i: instr,
                           home: Dict[Variable, arg]) -> instr:
        match i:
            case Instr(i_name, args):
                return Instr(i_name, [self.assign_homes_arg(arg, home) for arg in args])
            case _:
                return i

    def assign_homes_instrs(self, ss: List[instr],
                            home: Dict[Variable, arg]) -> List[instr]:
        return [self.assign_homes_instr(i, home) for i in ss]

    def assign_homes(self, p: X86Program) -> X86Program:
        home = dict()
        p.body = self.assign_homes_instrs(p.body, home)
        num_vars = len(home)
        p.stack_space = num_vars * 8 if num_vars % 2 == 0 else num_vars * 8 + 8
        return p

    ############################################################################
    # Patch Instructions
    ############################################################################

    def patch_instr(self, i: instr) -> List[instr]:
        match i:
            case Instr(i_name, [Deref(reg1, off1), Deref(reg2, off2)]):
                return [
                    Instr('movq', [Deref(reg1, off1), Reg('rax')]),
                    Instr(i_name, [Reg('rax'), Deref(reg2, off2)])
                ]
            case Instr(i_name, [Immediate(n), Deref(reg2, off2)]) if n > 2 ** 16:
                return [
                    Instr('movq', [Immediate(n), Reg('rax')]),
                    Instr(i_name, [Reg('rax'), Deref(reg2, off2)])
                ]
            case _:
                return [i]

    def patch_instrs(self, ss: List[instr]) -> List[instr]:
        res = []
        for s in ss:
            res.extend(self.patch_instr(s))
        return res

    def patch_instructions(self, p: X86Program) -> X86Program:
        new_p = p
        new_p.body = self.patch_instrs(p.body)
        return new_p

    ############################################################################
    # Prelude & Conclusion
    ############################################################################

    # def prelude_and_conclusion(self, p: X86Program) -> X86Program:
    #     # YOUR CODE HERE
    #     pass        

