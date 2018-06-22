# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import except_orm, ValidationError
import re
from datetime import datetime


class PappayaConcessionType(models.Model):
    _name='pappaya.concession.type'
    _rec_name = 'code' 
    
#     @api.model
#     def _default_society(self):
#         user_id = self.env['res.users'].sudo().browse(self.env.uid)
#         if len(user_id.company_id.parent_id)>0 and user_id.company_id.parent_id.type == 'society':
#             return user_id.company_id.parent_id.id
#         elif user_id.company_id.type == 'society':
#             return user_id.company_id.id
# 
#     @api.model
#     def _default_school(self):
#         user_id = self.env['res.users'].sudo().browse(self.env.uid)
#         if user_id.company_id and user_id.company_id.type == 'school':
#             return user_id.company_id.id
    
    name = fields.Char('Concession Name')
    society_ids =fields.Many2many('res.company','fee_concession_type_society_rel','fee_concession_type_id','society_id','Society')
    #~ society_id = fields.Many2one('res.company','Society', default=_default_society)
    school_ids = fields.Many2many('res.company','fee_concession_type_school_rel','fee_concession_type_id','school_id', 'School')
    fees_head_ids = fields.Many2many('pappaya.fees.head','concession_type_fees_head_rel','concession_type','fees_id', 'Fees Head')
    concession_fixed = fields.Selection([('staff_concession', 'Staff Concession'), ('sibling_concession', 'Sibling Concession')],string='Fixed Concession Name')
    type = fields.Boolean('Is Fixed Concession?', default=False)
    code = fields.Char('Code',size=6)
    
    @api.one
    def copy(self, default=None):
        raise ValidationError("You are not allowed to Duplicate")
    
    @api.one
    @api.constrains('code')
    def _check_unique_record(self):
        if self.code:
            if len(self.search([('school_ids', 'in', self.school_ids.ids), ('society_ids', 'in', self.society_ids.ids), ('code', '=', self.code)])) > 1:
                raise ValidationError("Record already exits. please click on Discard button to proceed")
    
    @api.onchange('type')
    def onchange_type(self):
        self.code = self.concession_fixed = None
        self.name = self.society_ids = self.school_ids = self.fees_head_ids= None
            
    @api.onchange('code')
    def onchange_code(self):
        if self.code:
            self.code = (self.code).upper()
    
    @api.onchange('concession_fixed')
    def onchange_default_concession(self):
        if self.concession_fixed == 'staff_concession':
            self.code = 'STFCON'
        elif self.concession_fixed == 'sibling_concession':
            self.code = 'SIBCON'
        
            
    @api.model
    def create(self, vals):
        if 'concession_fixed' in vals:
            if vals.get('concession_fixed') == 'staff_concession':
                vals['code'] = 'STFCON'
            elif vals.get('concession_fixed') == 'sibling_concession':
                vals['code'] = 'SIBCON'
        res = super(PappayaConcessionType, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        if 'concession_fixed' in vals:
            if vals.get('concession_fixed') == 'staff_concession':
                vals['code'] = 'STFCON'
            elif vals.get('concession_fixed') == 'sibling_concession':
                vals['code'] = 'SIBCON'
        res = super(PappayaConcessionType, self).write(vals)
        return res
    
    
            
    
    @api.onchange('society_ids')
    def _onchange_society_ids(self):
        if self.society_ids:
            self.school_ids = []
            return {'domain': {'school_ids': [('type', '=', 'school'),('parent_id', 'in', self.society_ids.ids)]}}


