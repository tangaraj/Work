# -*- coding: utf-8 -*-
import time
from openerp import models, fields, api, _
from openerp import workflow
from openerp.exceptions import ValidationError, UserError
from openerp.tools import amount_to_text_en
from datetime import datetime, date
from openerp.tools.misc import DEFAULT_SERVER_DATE_FORMAT




class PappayaFeesRefund(models.Model):
    _name='pappaya.fees.refund'
    _rec_name = 'student_id'
    
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
    
    society_id = fields.Many2one('res.company','Society', default=_default_society)
    school_id = fields.Many2one('res.company', 'School', default=_default_school)
    academic_year_id = fields.Many2one('academic.year', 'Academic Year')
    enrollment_number = fields.Char('Enrollment Number')
    grade_id = fields.Many2one('pappaya.grade', 'Class', required=1)
    student_id = fields.Many2one('pappaya.student', 'Student')
    refund_date = fields.Date('Refund Date')
    fee_refund_line = fields.One2many('pappaya.fees.refund.line','refund_id','Refund Line')
    payment_mode = fields.Selection([('cash','Cash'),('cheque/dd','Cheque'),('dd','DD'),('neft/rtgs','NEFT/RTGS')],string='Payment Mode')
    cheque_dd = fields.Char('Cheque/DD/POS/Ref. No')
    bank_name = fields.Char('Bank Name')
    remarks = fields.Text('Remarks')
    total = fields.Float('Total',compute='compute_total')
    
    
    
    @api.multi
    def get_school(self):
        school_list = []
        if self.school_id:
            vals = {}
            vals['school_id'] = self.school_id.name
            vals['logo'] = self.school_id.logo
            vals['street'] = self.school_id.street if self.school_id.street else ''
            vals['street2'] = self.school_id.street2 if self.school_id.street2 else ''
            vals['city'] = self.school_id.city if self.school_id.city else ''
            vals['zip'] = self.school_id.zip if self.school_id.zip else ''
            vals['phone'] = self.school_id.phone if self.school_id.phone else ''
            vals['fax'] = self.school_id.fax_id if self.school_id.fax_id else ''
            vals['email'] = self.school_id.email if self.school_id.email else ''
            vals['website'] = self.school_id.website if self.school_id.website else ''
            school_list.append(vals)
        return school_list
    
    @api.multi
    @api.depends('fee_refund_line.amount')
    def compute_total(self):
        for rec in self:
            rec.total = round(sum(line.amount for line in rec.fee_refund_line))
            
    
    @api.multi
    def amount_to_text_in(self, amount, currency):
        convert_amount_in_words2 = amount_to_text_en.amount_to_text(amount, lang='en', currency='')
        convert_change_in_words = convert_amount_in_words2.split(' and')[1]
        convert_change_in_words2 = convert_change_in_words.split(' Cent')[0] + ' Paise Only'
        if "Zero" in convert_amount_in_words2:
            convert_amount_in_words2 = convert_amount_in_words2.split(' and')[0] + ' Rupees Only'
        else:
            convert_amount_in_words2 = convert_amount_in_words2.split(' and')[0] + ' Rupees and ' + convert_change_in_words2
        return convert_amount_in_words2
    
    
    @api.multi
    def generate_refund_receipt_report(self):
        if self._context.get('active_ids'):
            return self.env['report'].get_action(self, 'pappaya_fees.report_original_fee_refund_receipt')
        if not self._context.get('active_ids'):
            return self.env['report'].get_action(self, 'pappaya_fees.report_duplicate_fee_refund_receipt')


class PappayaFeesRefundLine(models.Model):
    _name='pappaya.fees.refund.line'

    name = fields.Char('Fees Head')
    term_divide = fields.Selection([('1', 'Term-1'), ('2', 'Term-2'),('3','Term-3'),('4','Term-4'),('5','Term-5'),('6','Term-6'),('7','Term-7'),('8','Term-8'),('9','Term-9'),('10','Term-10')], string='Term No')
    amount = fields.Float('Amount')
    refund_id = fields.Many2one('pappaya.fees.refund','Refund')
