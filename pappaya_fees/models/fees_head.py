# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import except_orm, ValidationError
import re
from datetime import datetime




class Pappaya_fees_head(models.Model):
    _name = 'pappaya.fees.head'
    
    _sql_constraints = [('name_uniq', 'unique(name)', "Head Name already exists!")]
    
    name = fields.Char('Fees Head')
    is_term_divide = fields.Boolean('Is Term Divide')
    partial_payment = fields.Boolean('Partial Payment')
    


class Pappaya_fees_term(models.Model):
    _name = 'pappaya.fees.term'
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
    
    
    #~ name = fields.Char('Fees Term')
    #~ society_id = fields.Many2one('res.company','Society', domain=[('type','=','society')], default=_default_society)
    society_ids =fields.Many2many('res.company','society_fee_term_rel','term_id','society_id',string= 'Society')
    school_ids = fields.Many2many('res.company','fee_term_school_rel','term_id','school_id', string='School')
    #~ school_id = fields.Many2one('res.company', 'School', domain=[('type','=','school')], default=_default_school)
    academic_year_id = fields.Many2one('academic.year', 'Academic Year / Batch') 
    #~ fees_head_id = fields.Many2one('pappaya.fees.head','Fees Head') 
    no_of_terms = fields.Integer('No Of Terms')
    term_divide_ids = fields.One2many('pappaya.term.divide', 'term_id','Fees Term')
    total = fields.Integer('Total')
    term_bool = fields.Boolean('Compute')
   

    @api.onchange('school_ids')
    def onchange_school(self):
        self.academic_year_id = None
        self.term_divide_ids = None
        self.no_of_terms = None
        self.term_bool = False
        self.academic_year_id = []
        academic_year_id_list = []
        for school_id in self.school_ids:
            for ac_obj in self.env['academic.year'].search([('is_active','=',True)]):
                if school_id.id in ac_obj.school_id.ids and ac_obj.id not in academic_year_id_list:
                    academic_year_id_list.append(ac_obj.id)
        return {'domain': {'academic_year_id': [('id', 'in', academic_year_id_list)]}}
                
    @api.onchange('society_ids')
    def _onchange_society_ids(self):
        if self.society_ids:
            self.school_ids = []
            self.term_divide_ids = None
            self.no_of_terms = None
            self.term_bool = False
            return {'domain': {'school_ids': [('type', '=', 'school'),('parent_id', 'in', self.society_ids.ids)]}}
    
   
    @api.constrains('no_of_terms')
    def _check_pay_amount(self):
        if self.no_of_terms < 0 or self.no_of_terms <= 0:
            raise ValidationError(_("Term number should be positive and greater than 0"))
    
       
    
    @api.multi
    @api.constrains('academic_year_id')
    def _check_unique_name(self):
        if self.academic_year_id.id:
            if len(self.search([('academic_year_id','=',self.academic_year_id.id),('school_ids','in',self.school_ids.ids)]).ids)>1:
                raise ValidationError("Fee Term for the selected school already exists")
    
    @api.constrains('total', 'term_divide_ids')
    def check_total(self):
        if self.total != 100 and self.total != 0:
            raise ValidationError("Please ensure total term breakage is 100%")
        count = 0
        for t in self.term_divide_ids:
            count += 1
            if self.no_of_terms >= count:
                if t.percentage == 0.0:
                    raise ValidationError("Percentage should not be zero")
            for r in self:
                if r.academic_year_id.start_date:
                    if t.start_date and t.start_date < r.academic_year_id.start_date:
                        raise ValidationError("Start date should be within academic year")
                if r.academic_year_id.end_date:
                    if t.end_date and t.end_date > r.academic_year_id.end_date:
                        raise ValidationError("End date should be within academic year")
                if t.end_date < t.start_date:
                    raise ValidationError("End date should be greater than start date")
                        
            
    
    
    
    @api.onchange('term_divide_ids','term_divide_ids.line')
    def compute_total(self):
        tot = 0
        count = 0 
        for line in self.term_divide_ids:
            count += 1
            if self.no_of_terms >= count:
                tot += line.percentage
        self.total = tot
	#~ if self.total != 100:
	    #~ raise ValidationError("Please ensure total term breakage is 100%")

    
    
    @api.multi
    def compute_term(self):
        terms_line = self.env['pappaya.term.divide']
        terms_line.search([('term_id', '=', self.id)]).unlink()
        counter = 1
        i = 1
        for term in range(1,self.no_of_terms + 1):
            line_id = terms_line.create({ 
                       'name':str(term),
                       'term':str(term),
                       'term_id':self.id})
            counter += 1
            i = i + 1
        self.write({'term_bool':True})
        return True
    
    @api.model
    def create(self, vals):
        res = super(Pappaya_fees_term, self).create(vals)
        if vals.get('term_divide_ids') and res.no_of_terms:
            count = len(vals.get('term_divide_ids'))
            if count > res.no_of_terms:
                line_count = 0
                for term_line in res.term_divide_ids:
                    line_count += 1
                    if line_count > res.no_of_terms:
                        term_line.sudo().unlink()
        return res

    @api.multi
    def write(self, vals):
        res = super(Pappaya_fees_term, self).write(vals)
        if vals.get('term_divide_ids') and self.no_of_terms:
            count = len(vals.get('term_divide_ids'))
            if count > self.no_of_terms:
                line_count = 0
                for term_line in self.term_divide_ids:
                    line_count += 1
                    if line_count > self.no_of_terms:
                        term_line.sudo().unlink()
        return res
    
class Pappaya_term_divide(models.Model):
    _name = 'pappaya.term.divide'
        
    name = fields.Char('Term Name')
    term = fields.Selection([('1', 'Term-1'), ('2', 'Term-2'),('3','Term-3'),('4','Term-4'),('5','Term-5'),('6','Term-6'),('7','Term-7'),('8','Term-8'),('9','Term-9'),('10','Term-10')], string='Term')
    percentage = fields.Integer('Percentage')
    term_id = fields.Many2one('pappaya.fees.term' ,'Fees Term')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')

    @api.constrains('percentage')
    def _check_pay_amount(self):
        if self.percentage < 0:
           raise ValidationError(_("Percentage should be positive"))
    

        
	    
    
    

        
        
        
        
        


