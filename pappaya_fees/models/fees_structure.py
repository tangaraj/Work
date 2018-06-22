# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import except_orm, ValidationError
import re
from datetime import datetime


class Pappaya_fees_structure(models.Model):
    _name = 'pappaya.fees.structure'
    _rec_name = 'academic_year_id'
    
    @api.model
    def _default_society(self):
        user_id = self.env['res.users'].sudo().browse(self.env.uid)
        if len(user_id.company_id.parent_id)>0 and user_id.company_id.parent_id.type == 'society':
            return user_id.company_id.parent_id.id
        elif user_id.company_id.type == 'society':
            return user_id.company_id.id

    @api.model
    def _default_school(self):
        user_id = self.env['res.users'].sudo().browse(self.env.uid)
        if user_id.company_id and user_id.company_id.type == 'school':
            return user_id.company_id.id
        
        
        
    @api.onchange('school_ids')
    def onchange_school(self):
        if not self.society_ids:
            self.school_ids = []
    
    
    #~ name = fields.Char('Fees Structure')
    #~ society_id = fields.Many2one('res.company','Society', domain=[('type','=','society')], default=_default_society)
    #~ school_id = fields.Many2one('res.company', 'School', domain=[('type','=','school')], default=_default_school)
    society_ids =fields.Many2many('res.company','society_fee_structure_rel','structure_id','society_id',string= 'Society')
    school_ids = fields.Many2many('res.company','fee_structure_school_rel','structure_id','school_id', string='School')
    academic_year_id = fields.Many2one('academic.year', 'Academic Year')
    grade_ids_m2m = fields.Many2many('pappaya.grade', string='Class')
    fee_head_line =fields.One2many('pappaya.fees.head.line','structure_id' ,'Fees head')
    fee_term_line = fields.One2many('pappaya.fees.term.line','structure_id','Fees Term')
 
    
    @api.multi
    @api.constrains('academic_year_id')
    def _check_unique_name(self):
        if self.academic_year_id.id:
            if len(self.search([('grade_ids_m2m','in',self.grade_ids_m2m.ids),('school_ids','in',self.school_ids.ids),('academic_year_id','=',self.academic_year_id.id)]).ids)>1:
                raise ValidationError("Fee structure for the selected Classes already exists")
    
    
    
    @api.onchange('society_ids')
    def _onchange_society_ids(self):
        if self.society_ids:
	    #~ self.fee_term_line = None
            self.school_ids = []
            return {'domain': {'school_ids': [('type', '=', 'school'),('parent_id', 'in', self.society_ids.ids)]}}
    
    
    
    @api.onchange('school_ids')
    def onchange_school(self):
        if not self.fee_head_line:
            fee_head = self.env['pappaya.fees.head'].search([])
            ids = []
            for i in fee_head:
                ids.append({
                        'head_id': i.id,
                        'partial_payment':i.partial_payment,
                        'structure_id':self.id   
                    })
            self.update({'fee_head_line':ids})
	#~ self.academic_year_id = []
    	academic_year_id_list = []
    	for school_id in self.school_ids:
    	    for ac_obj in self.env['academic.year'].search([('is_active','=',True)]):
    		if school_id.id in ac_obj.school_id.ids and ac_obj.id not in academic_year_id_list:
    		    academic_year_id_list.append(ac_obj.id)
    	return {'domain': {'academic_year_id': [('id', 'in', academic_year_id_list)]}}
	    
    #~ @api.multi
    #~ def write(self, vals):
        #~ school_id = vals.get('school_id', False)
        # if vals.get('school_id'):
        #     academic_year_id = self.env['academic.year'].search([('is_active','=', True),('school_id','in', vals.get('school_id'))])[0].id
        #     vals['academic_year_id'] = academic_year_id
        #~ return super(Pappaya_fees_structure, self).write(vals)
    
    #~ @api.model
    #~ def create(self, vals):
        #~ school_id = vals.get('school_id', False)
        # if vals.get('school_id'):
        #     academic_year_id = self.env['academic.year'].search([('is_active','=', True),('school_id','in', vals.get('school_id'))])[0].id
        #     vals['academic_year_id'] = academic_year_id
        #~ res = super(Pappaya_fees_structure, self).create(vals)
        #~ return res

    @api.multi       
    def generate_fees(self):
         fee_line_head = self.env['pappaya.fees.head.line']
         fee_line_term = self.env['pappaya.fees.term.line']
         f_term = self.env['pappaya.fees.term']
         fee_line_term.search([('structure_id', '=', self.id)]).sudo().unlink()
         ft_srch = f_term.search([('school_ids','in' ,self.school_ids.ids),('academic_year_id','=',self.academic_year_id.id)])
         
         for f in self.fee_head_line:
            if f.amount > 0.00:
                if not f.head_id.is_term_divide:
                    fee_line_term.sudo().create({'structure_id':self.id,'name':f.head_id.name,'partial_payment':f.partial_payment,'amount':f.amount})
                elif f.head_id.is_term_divide:
                    for i in ft_srch:
                        for j in ft_srch.term_divide_ids:
                            fee_line_term.sudo().create({'structure_id':self.id,
                                                  'name': f.head_id.name + '-' +'Term-'+ str(j.name),
                                                  'term_divide':j.term,
                                                  'partial_payment':f.partial_payment,
                                                  'amount':f.amount * j.percentage/100 ,
                                                  'percentage':j.percentage})
                


class Pappaya_fees_head_line(models.Model):
    _name='pappaya.fees.head.line'
    
    head_id = fields.Many2one('pappaya.fees.head','Fees Head')
    amount = fields.Float('Amount')
    partial_payment = fields.Boolean('Partial Payment')
    structure_id = fields.Many2one('pappaya.fees.structure','Fees Structure')
    
    @api.constrains('amount')
    def _check_pay_amount(self):
	if self.amount < 0:
	   raise ValidationError(_("The value of amount should be positive"))

    
    
class Pappaya_fees_term_line(models.Model):
    _name = 'pappaya.fees.term.line'
    
    name = fields.Char('Name')
    term_id = fields.Many2one('pappaya.fees.term','Term')
    term_divide = fields.Selection([('1', 'Term-1'), ('2', 'Term-2'),('3','Term-3'),('4','Term-4'),('5','Term-5'),('6','Term-6'),('7','Term-7'),('8','Term-8'),('9','Term-9'),('10','Term-10')], string='Term')
    partial_payment = fields.Boolean('Partial Payment')
    amount = fields.Float('Amount')
    percentage = fields.Float('Percentage')
    structure_id = fields.Many2one('pappaya.fees.structure','Fees Structure')
    head_id = fields.Many2one('pappaya.fees.head','Fees Head')
    
    
    
    
    
