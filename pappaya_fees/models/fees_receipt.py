# -*- coding: utf-8 -*-
import time
import os
from openerp import models, fields, api, _
from openerp import workflow
from openerp.exceptions import ValidationError, UserError
from openerp.tools import amount_to_text_en
from datetime import datetime, date
from openerp.tools.misc import DEFAULT_SERVER_DATE_FORMAT

class PappayaFeesReceipt(models.Model):
    _name = 'pappaya.fees.receipt'

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
    
    name =  fields.Char('Fee Receipt')
    society_id = fields.Many2one('res.company','Society', default=_default_society)
    school_id = fields.Many2one('res.company', 'School', default=_default_school)
    school_code = fields.Char(related='school_id.school_code', string='School Code')
    academic_year_id = fields.Many2one('academic.year', 'Academic Year')
    enrollment_number = fields.Char('Enrollment Number')
    grade_id = fields.Many2one('pappaya.grade', 'Class', required=1)
    student_id = fields.Many2one('pappaya.student', 'Student')
    fees_receipt_line =  fields.One2many('pappaya.fees.receipt.line','receipt_id','Receipt Line')
    receipt_date = fields.Date('Receipt Date')
    payment_mode = fields.Selection([('cash','Cash'),('cheque/dd','Cheque'),('dd','DD'),('neft/rtgs','Neft/RTGS'),('card','POS')],string='Payment Mode')
    cheque_dd = fields.Char('Cheque/DD/POS/Ref. No')
    bank_name = fields.Char('Bank Name')
    remarks = fields.Text('Remarks')
    total = fields.Float('Total', compute ='compute_total')
    state = fields.Selection([('paid','Paid'),('refund','Refunded'),('waiting_approval','Waiting for Approval'),('cancel','Cancel')],string='Status', default="paid")
    fee_collection_id = fields.Many2one('pappaya.fees.collection', 'Collection ID')
    pay_due_total = fields.Float('Actual Pay due')
    receipt_status = fields.Selection([('cleared','Cleared'),('uncleared','Uncleared')], string='Status', default='uncleared')
    is_select = fields.Boolean(string='Select')
    bank_id = fields.Many2one('bank.status', string='Bank')
    bank_deposit_attachments = fields.Many2many('ir.attachment', string="Attachments")
    
    @api.one    
    @api.onchange('bank_deposit_attachments')
    def attach_getFilename(self):
        today = time.strftime('%d_%b_%Y_')
        count = 1
        for attachment in self.bank_deposit_attachments:
            name, ext = os.path.splitext(attachment.name)
            attachment.write({'name':str(today) + (str(count)) +  ext,'datas_fname':str(today) + (str(count)) +  ext})
            count += 1
    
    @api.multi
    @api.depends('fees_receipt_line.amount')
    def compute_total(self):
        for rec in self:
            rec.total = sum(line.amount for line in rec.fees_receipt_line )

    @api.model
    def create(self, vals):
        res = super(PappayaFeesReceipt, self).create(vals)
        school_id = vals.get('school_id', False)
        academic_year_id = vals.get('academic_year_id',False)
        students_details = self.search([('school_id', '=', school_id),('academic_year_id','=',academic_year_id)]).ids
        sequence_no =  (len(students_details) -1) + 1
        sequence_no = "%0.4d" % sequence_no
        school=self.env['pappaya.fees.receipt'].browse(res.ids[0])
        sequence = str(school.school_id.code) + str(school.receipt_date).replace('-','') +  str(sequence_no)
        res['name'] = sequence
        return res

    @api.multi    
    def cancel_approval(self):
        self.write({'state':'waiting_approval'})
        
    @api.multi    
    def cancel_approved(self):
        if self.payment_mode == 'cash':
            receipt_total = 0.0
            deposit_details = self.env['bank.deposit'].search([('school_id', '=', self.school_id.id), ('society_id', '=', self.society_id.id), ('academic_year_id', '=', self.academic_year_id.id),('state','=','approved')])
            for deposit in deposit_details:
                for lines in deposit.cash_receipt_ids:
                    for line in lines:
                        if line.id == self.id:
                            receipt_total += line.total
            
            deposit_details = self.env['bank.deposit'].search([('school_id', '=', self.school_id.id), ('society_id', '=', self.society_id.id), ('academic_year_id', '=', self.academic_year_id.id)], limit=1, order="id desc")
            last_balance = deposit_details.closing_bal - receipt_total
            deposit_details.write({'closing_bal':last_balance, 'cancel_remarks':'Receipt No.'+' '+str(self.name)+'Amount:'+str(self.total)})
        else:
            deposit_details = self.env['bank.deposit.clearance'].search([('school_id', '=', self.school_id.id), ('society_id', '=', self.society_id.id), ('academic_year_id', '=', self.academic_year_id.id)])
            for deposit in deposit_details:
                for lines in deposit.status_line_ids:
                    for line in lines:
                        if line.receipt_id.id == self.id and line.state == 'cleared':
                            line.write({'state':'rejected'})

        if self.fee_collection_id:
            for receipt_line in self.fees_receipt_line:
                for collection_line in self.fee_collection_id.fees_collection_line:
                    if receipt_line.name == collection_line.name:
                        if collection_line.total_paid == receipt_line.amount:
                            collection_line.write({'due_amount':(collection_line.due_amount + receipt_line.amount),
                                                   'total_paid':(collection_line.total_paid - receipt_line.amount),
                                                   'pay':False,
                                                   'term_state':'due' })
                fees_ledger = self.env['pappaya.fees.ledger'].search([('fee_collection_id', '=', self.fee_collection_id.id)]) 
                
                if fees_ledger:
                    for ledger in  fees_ledger:
                        if ledger.fee_ledger_line:
                            for ledger_line in ledger.fee_ledger_line:
                                if ledger_line.name ==  receipt_line.name:
                                    ledger_line.write({
                                        'debit':ledger_line.debit - receipt_line.amount,
                                        'balance':ledger_line.balance + receipt_line.amount
                                        })
#                         if ledger.fee_receipt_ledger_line:
#                             for ledger_receipt_line in ledger.fee_receipt_ledger_line:
#                                 if ledger_receipt_line.fees_receipt_id.id == self.id and self.name == ledger_receipt_line.fees_receipt_id.name:
#                                     
#                                     if ledger_receipt_line.fees_head ==  receipt_line.name:
#                                         print datetime.now().date(),"datetime.now().date()",type(datetime.now().date())
#                                         if ledger_receipt_line.transaction:
#                                             ledger_receipt_line.write({'transaction':str(ledger_receipt_line.transaction) + ' - ' + 'Canceled Receipt on :' + datetime.strptime(str(datetime.now().date()),DEFAULT_SERVER_DATE_FORMAT).strftime('%d/%b/%Y')})
#                                         else:
#                                             ledger_receipt_line.write({'transaction':'Canceled Receipt on :' + datetime.strptime(str(datetime.now().date()),DEFAULT_SERVER_DATE_FORMAT).strftime('%d/%b/%Y') })
                        
            fee_cancel_ledger_line = []
#             fees_ledger = self.env['pappaya.fees.ledger'].search([('fee_collection_id', '=', self.fee_collection_id.id)])            
            for frl in self.fees_receipt_line:
                fee_cancel_ledger_line.append((0, 0, 
                                            {
                                    'posting_date':datetime.now().date(),
                                    'fees_head':frl.name,
                                    'amount':frl.amount,
                                            }))
            fees_ledger.fee_cancel_ledger_line = fee_cancel_ledger_line
                            
        self.write({'state':'cancel'})
        
        
    @api.multi
    def cancel_rejected(self):
        self.write({'state':'paid'})

    # Below Functionality related to Reports
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
    def due_calc(self):
        due_amount = 0.00
        for record in self.fee_collection_id:
            for rec_line in record.fees_collection_line:
                if not rec_line.pay and rec_line.term_state == 'due' and not due_amount:
                    due_amount = rec_line.due_amount
        return due_amount

    @api.multi
    def next_due_date_and_amount(self):
        date, term_list = '', []
        due_amount = 0.00
        exit_loop = False
        for record in self.fee_collection_id:
            term_obj = self.env['pappaya.fees.term'].search(
                [('society_ids', 'in', record.society_id.id), ('school_ids', 'in', record.school_id.id),
                 ('academic_year_id', '=', record.academic_year_id.id)])
            if not exit_loop:
                if self.receipt_date:
                    term = False
                    for term in term_obj:
                        for termline in term.term_divide_ids:
                            if termline.start_date and termline.end_date and self.receipt_date >= termline.start_date and self.receipt_date <= termline.end_date :
                                term = True
                                date = datetime.strptime(str(termline.end_date), DEFAULT_SERVER_DATE_FORMAT).strftime("%d/%b/%Y")
                                
                                for rec_line in record.fees_collection_line:
                                    if not exit_loop:
                                        due_amount += rec_line.due_amount
                                        if rec_line.term_divide == termline.term:
                                            exit_loop = True
            if due_amount == 0.00:
                due_amount = record.due_total
        return {'due_amount':due_amount,'due_date':date}
    
    @api.multi
    def next_due_date_and_payment_details(self):
        data = []
        for record in self.fee_collection_id:
            term_obj = self.env['pappaya.fees.term'].search(
                [('society_ids', 'in', record.society_id.id), ('school_ids', 'in', record.school_id.id),
                 ('academic_year_id', '=', record.academic_year_id.id)])
            if record.bulk_term_state == 'due':
                for rec_line in record.fees_collection_line:
                    if rec_line.due_amount and not rec_line.pay and rec_line.term_state == 'due':
                        date = ''
                        for term in term_obj:
                            for termline in term.term_divide_ids:
                                if rec_line.term_divide == termline.term:
                                    if termline.start_date:
                                        date = datetime.strptime(str(termline.start_date), DEFAULT_SERVER_DATE_FORMAT).strftime("%d/%b/%Y")
                                    
                        data.append({
                                        'fee_type':rec_line.name,
                                        'due_amount':rec_line.due_amount,
                                        'due_date':date
                                        
                                        })
        return data 

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
    def get_value(self):
        mode_dict = {'cash': 'Cash','cheque/dd':'Cheque', 'dd':'DD','neft/rtgs':'Neft/RTGS','card':'PoS'}
        payment_mode = ''
        if self.payment_mode and self.payment_mode in ['cash','card','neft/rtgs']:
            payment_mode = mode_dict[self.payment_mode]
        if self.payment_mode and self.payment_mode in ['cheque/dd','dd']:
            payment_mode = mode_dict[self.payment_mode] + ' Subject to realisation'
        return payment_mode
    
    @api.multi
    def get_value_duplicate(self):
        mode_dict = {'cash': 'Cash','cheque/dd':'Cheque', 'dd':'DD','neft/rtgs':'Neft/RTGS','card':'PoS'}
        payment_mode = ''
        if self.payment_mode and self.payment_mode in ['cash','card','neft/rtgs','cheque/dd','dd']:
            payment_mode = mode_dict[self.payment_mode]
        return payment_mode

    @api.multi
    def generate_receipt_report(self):
        if self._context.get('active_ids'):
            return self.env['report'].get_action(self, 'pappaya_fees.report_original_fee_receipt')
        if not self._context.get('active_ids'):
            return self.env['report'].get_action(self, 'pappaya_fees.report_duplicate_fee_receipt')
        
        
    @api.multi
    def view_all_ledger_details(self):
        print self,"3444444444444"
        print self.fee_collection_id,"2222222222222222222"
        if self.fee_collection_id:
            ledger_id = self.env['pappaya.fees.ledger'].search([('fee_collection_id' , '=', self.fee_collection_id.id)])[0]
            print ledger_id,"edddddddddddddddddddd"
            form_view = self.env.ref('pappaya_fees.pappaya_fees_ledger_form')
            #tree_view = self.env.ref('pappaya_fees.pappaya_fees_ledger_tree')
            if ledger_id:
                value = {
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'pappaya.fees.ledger',
                    'view_id': False,
                    'views': [(form_view and form_view.id or False, 'form')],
                    'type': 'ir.actions.act_window',
                    'res_id': ledger_id.id,
                    'target': 'new',
                    'nodestroy': True
                    
                }
                return value
        
        

class PappayaFeesReceiptLine(models.Model):
    _name = 'pappaya.fees.receipt.line'
    
    name = fields.Char('Fees Head')
    term_divide = fields.Selection([('1', 'Term-1'), ('2', 'Term-2'),('3','Term-3'),('4','Term-4'),('5','Term-5'),('6','Term-6'),('7','Term-7'),('8','Term-8'),('9','Term-9'),('10','Term-10')], string='Term No')
    amount = fields.Float('Amount')
    concession_amount = fields.Float('Concession')
    receipt_id = fields.Many2one('pappaya.fees.receipt', 'Receipt')
    
    
    
