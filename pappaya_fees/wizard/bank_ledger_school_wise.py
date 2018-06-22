import time
from openerp import models, fields, api, _
from openerp.exceptions import ValidationError, UserError
from openerp.tools.misc import DEFAULT_SERVER_DATE_FORMAT
import xlwt
import cStringIO
import base64
from openerp.http import request
from datetime import datetime, date
from cStringIO import StringIO
from datetime import date
import datetime
from datetime import timedelta
import pytz
import os
from PIL import Image
from xlwt import *

class BankLedgerSchoolWise(models.TransientModel):
    _name = "bank.ledger.school.wise"

    @api.model
    def _default_society(self):
        user_id = self.env['res.users'].sudo().browse(self.env.uid)
        if len(user_id.company_id.parent_id) > 0 and user_id.company_id.parent_id.type == 'society':
            return user_id.company_id.parent_id.id
        elif user_id.company_id.type == 'society':
            return user_id.company_id.id

    @api.model
    def _default_school(self):
        user_id = self.env['res.users'].sudo().browse(self.env.uid)
        if user_id.company_id and user_id.company_id.type == 'school':
            return user_id.company_id.id

#     society_id =fields.Many2one('res.company',string= 'Society', default=_default_society)
#     school_id = fields.Many2one('res.company',string='School', default=_default_school)

    society_ids =fields.Many2many('res.company','society_bank_ledger_school_wise_rel','company_id','society_id',string= 'Society')
    school_ids = fields.Many2many('res.company','school_bank_ledger_school_wise_rel','company_id','school_id', string='School')
    academic_year_id = fields.Many2one('academic.year',string='Academic Year')
    bank_account_id = fields.Many2one('bank.account.config', string='Bank Name')
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')

#     @api.onchange('society_ids')
#     def _onchange_society_ids(self):
#         if self.society_ids:
#             self.school_ids = []
#             return {'domain': {'school_ids': [('type', '=', 'school'),('parent_id', 'in', self.society_ids.ids)]}}



#     @api.onchange('school_ids')
#     def onchange_school(self):
#         self.academic_year_id = []
#         if not self.society_ids:
#             self.school_ids = []
#         return {'domain': {'academic_year_id': [('school_id', 'in', self.school_ids.ids)]}}
    

    @api.multi
    def get_school_header(self):
        school_list = []
        if (len(self.school_ids) == 1 and len(self.society_ids) == 1) or (
                len(self.school_ids) == 1 and not self.society_ids):
            vals = {}
            vals['school_id'] = self.school_ids.name
            vals['logo'] = self.school_ids.logo if self.school_ids.logo else ''
            vals['street'] = self.school_ids.street if self.school_ids.street else ''
            vals['street2'] = self.school_ids.street2 if self.school_ids.street2 else ''
            vals['city'] = self.school_ids.city if self.school_ids.city else ''
            vals['zip'] = self.school_ids.zip if self.school_ids.zip else ''
            vals['phone'] = self.school_ids.phone if self.school_ids.phone else ''
            vals['fax'] = self.school_ids.fax_id if self.school_ids.fax_id else ''
            vals['email'] = self.school_ids.email if self.school_ids.email else ''
            vals['website'] = self.school_ids.website if self.school_ids.website else ''
            school_list.append(vals)
        if (len(self.society_ids) == 1 and not self.school_ids):
            vals = {}
            vals['school_id'] = self.society_ids.name
            vals['logo'] = self.society_ids.logo
            vals['street'] = self.society_ids.street if self.society_ids.street else ''
            vals['street2'] = self.society_ids.street2 if self.society_ids.street2 else ''
            vals['city'] = self.society_ids.city if self.society_ids.city else ''
            vals['zip'] = self.society_ids.zip if self.society_ids.zip else ''
            vals['phone'] = self.society_ids.phone if self.society_ids.phone else ''
            vals['fax'] = self.society_ids.fax_id if self.society_ids.fax_id else ''
            vals['email'] = self.society_ids.email if self.society_ids.email else ''
            vals['website'] = self.society_ids.website if self.society_ids.website else ''
            school_list.append(vals)
        if (len(self.society_ids) == 1 and len(self.school_ids) != 1):
            vals = {}
            vals['school_id'] = self.society_ids.name
            vals['logo'] = self.society_ids.logo
            vals['street'] = self.society_ids.street if self.society_ids.street else ''
            vals['street2'] = self.society_ids.street2 if self.society_ids.street2 else ''
            vals['city'] = self.society_ids.city if self.society_ids.city else ''
            vals['zip'] = self.society_ids.zip if self.society_ids.zip else ''
            vals['phone'] = self.society_ids.phone if self.society_ids.phone else ''
            vals['fax'] = self.society_ids.fax_id if self.society_ids.fax_id else ''
            vals['email'] = self.society_ids.email if self.society_ids.email else ''
            vals['website'] = self.society_ids.website if self.society_ids.website else ''
            school_list.append(vals)
        return school_list

    @api.multi
    def get_society_header(self):
        society_list = []
        if not self.society_ids and not self.school_ids:
            soc_list = ''
            obj = self.env['res.company'].sudo().search([('type', '=', 'society')])
            for record in obj:
                soc_list += str(record.name) + ', '
            vals = {}
            vals['society_id'] = soc_list[:-2]
            society_list.append(vals)
        else:
            sc_list = ''
            for record in self.society_ids:
                sc_list += str(record.name) + ', '
            vals = {}
            vals['society_id'] = sc_list[:-2]
            society_list.append(vals)
        return society_list

    @api.multi
    def get_data(self):
        data=[]
        domain = []
        if self.society_ids:
            domain.append(('society_id','in',self.society_ids.ids))
        if self.school_ids:
            domain.append(('school_id','in',self.school_ids.ids))
        if self.academic_year_id:
            domain.append(('academic_year_id','=',self.academic_year_id.id))
        if self.bank_account_id:
            domain.append(('bank_id', '=', self.bank_account_id.id))
        domain.append(('state','in',['requested','approved']))
        deposit_obj = self.env['bank.deposit'].sudo().search(domain, order="id desc",limit=1)
        s_no = 0 
        for obj in deposit_obj:
            s_no += 1
            unclr,clr = 0.0,0.0
            date = datetime.datetime.strptime(str(obj.deposit_date),DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
            if obj.state == 'requested':
                unclr += obj.c_amt_deposit
            if obj.state == 'approved':
                clr += obj.c_amt_deposit
            
            data.append({
                        's_no':s_no,
                        'date':date,
                        'school':obj.school_id.name,
                        'opening_balance':obj.opening_bal,
                        'cash_collection':obj.total_cash_amt,
                        'bank_deposit':clr,
                        'closing_balance':obj.closing_bal,
                        'uncleared_deposit':unclr
                        })
        return data
    
    @api.multi
    def from_data(self):
        workbook = xlwt.Workbook()
        company_name = xlwt.easyxf('font: name Times New Roman, height 350, bold on; align: wrap on, vert centre, horiz centre;')
        company_address = xlwt.easyxf('font: name Times New Roman, height 230, bold on; align: wrap on, vert centre, horiz centre;')
        header = xlwt.easyxf('font: name Times New Roman, height 200, bold on,italic off; align: wrap on, vert centre, horiz centre;  borders: top thin, bottom thin, left thin, right thin;')
        answer = xlwt.easyxf('font: name Times New Roman, height 200; borders: top thin, bottom thin, left thin, right thin;')

        sheet_name = 'Cask Book School Wise'
        sheet = workbook.add_sheet(sheet_name)
        sheet.row(0).height = 450;

        style_header_without_border = XFStyle()
        fnt = Font()
        fnt.bold = True
        fnt.height = 12*0x14
        style_header_without_border.font = fnt
        al1 = Alignment()
        al1.horz = Alignment.HORZ_CENTER
        al1.vert = Alignment.VERT_CENTER
        pat2 = Pattern()
        style_header_without_border.alignment = al1
        style_header_without_border.pattern = pat2

        style_center_align_without_border = XFStyle()
        al_c = Alignment()
        al_c.horz = Alignment.HORZ_CENTER
        al_c.vert = Alignment.VERT_CENTER
        style_center_align_without_border.alignment = al_c

        row_no = 0

        # cwd = os.path.abspath(__file__)
        # path = cwd.rsplit('/', 2)
        # image_path = path[0] + '/static/src/img/dis_logo1.bmp'
        # image_path = image_path.replace("pappaya_fees", "pappaya_core")
        # sheet.write_merge(0,4,0,0,'',style_center_align_without_border)
        #
        # sheet.insert_bitmap(image_path, 0, 0, scale_x = .3, scale_y = .4)

        if (len(self.school_ids) == 1 and len(self.society_ids) == 1) or (len(self.school_ids) == 1 and not self.society_ids):
            sheet.write_merge(row_no, row_no, 0, 7, self.school_ids.name if self.school_ids.name else '', style_header_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 7, (self.school_ids.street if self.school_ids.street else ''), style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 7, (self.school_ids.street2 if self.school_ids.street2 else '') + ', ' +(self.school_ids.city if self.school_ids.city else ''), style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 7, 'P.O Box: ' + (self.school_ids.street2 if self.school_ids.street2 else ''), style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 7, 'Tel: ' + (self.school_ids.phone if self.school_ids.phone else '') + ', ' + 'Fax: ' + (self.school_ids.fax if self.school_ids.fax else '') + ', ' + 'Email: ' + (self.school_ids.email if self.school_ids.email else ''), style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 7, self.school_ids.website if self.school_ids.website else '', style_center_align_without_border)
            row_no += 2
            sheet.write_merge(row_no, row_no, 0, 7, 'Cask Book School Wise', company_address)
        if (len(self.society_ids) == 1 and not self.school_ids) or (len(self.society_ids) == 1 and len(self.school_ids) > 1):
            sheet.write_merge(row_no, row_no, 0, 7, self.society_ids.name if self.society_ids.name else '',style_header_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 7, (self.society_ids.street if self.society_ids.street else ''),style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 7,(self.society_ids.street2 if self.society_ids.street2 else '') + ', ' + (self.society_ids.city if self.society_ids.city else ''), style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 7,'P.O Box: ' + (self.society_ids.street2 if self.society_ids.street2 else ''),style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 7,
                              'Tel: ' + (self.society_ids.phone if self.society_ids.phone else '') + ', ' + 'Fax: ' + (self.society_ids.fax if self.society_ids.fax else '') + ', ' + 'Email: ' + (self.society_ids.email if self.society_ids.email else ''),style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 7, self.society_ids.website if self.society_ids.website else '',style_center_align_without_border)
            row_no += 2
            sheet.write_merge(row_no, row_no, 0, 7, 'Cask Book School Wise', company_address)
        if (not self.society_ids and not self.school_ids) or (len(self.school_ids) > 1 and not self.society_ids):
            soc_list = ''
            obj = self.env['res.company'].sudo().search([('type', '=', 'society')])
            for record in obj:
                soc_list += str(record.name) + ', '
            sheet.write_merge(row_no, row_no, 0, 7,'')
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 7,'')
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 7,soc_list[:-2],company_address)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 7,'')
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 7,'')
            row_no += 2
            sheet.write_merge(row_no, row_no, 0, 7, 'Cask Book School Wise', company_address)
        if (len(self.society_ids) > 1) or (len(self.society_ids) > 1 and len(self.school_ids) > 1):
            sc_list = ''
            for record in self.society_ids:
                sc_list += str(record.name) + ', '
            sheet.write_merge(row_no, row_no, 0, 7,'')
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 7,'')
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 7, sc_list[:-2],company_address)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 7,'')
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 7,'')
            row_no += 2
            sheet.write_merge(row_no,row_no,0,7, 'Cask Book School Wise', company_address)
            
        row_no += 1    
        sheet.write_merge(row_no,row_no,0,7, self.bank_account_id.display_name, company_address)
#         row_no += 1    
#         sheet.write_merge(row_no,row_no,0,7, datetime.datetime.strptime(str(self.from_date),DEFAULT_SERVER_DATE_FORMAT).strftime('%d/%b/%Y') + ' to ' + datetime.datetime.strptime(str(self.to_date),DEFAULT_SERVER_DATE_FORMAT).strftime('%d/%b/%Y'), company_address)    

        row_no += 3
        sheet.row(row_no).height = 350;
        sheet.col(0).width = 256 * 17
        sheet.write(row_no, 0, 'S.No', header)
        sheet.col(1).width = 256 * 17
        sheet.write(row_no, 1, 'Date', header)
        sheet.col(2).width = 256 * 17
        sheet.write(row_no, 2, 'School', header)
        sheet.col(3).width = 256 * 17
        sheet.write(row_no, 3, 'Opening Balance', header)
        sheet.col(4).width = 256 * 17
        sheet.write(row_no, 4, 'Cash Collection', header)
        sheet.col(5).width = 256 * 17
        sheet.write(row_no, 5, 'Bank Deposit', header)
        sheet.col(6).width = 256 * 17
        sheet.write(row_no, 6, 'Closing Balance', header)
        sheet.col(7).width = 256 * 17
        sheet.write(row_no, 7, 'Uncleared Deposit', header)
        row_no += 1
        
        for data in self.get_data():
            sheet.write(row_no, 0, data['s_no'] , answer)
            sheet.write(row_no, 1, data['date'] , answer)
            sheet.write(row_no, 2, data['school'] , answer)
            sheet.write(row_no, 3, data['opening_balance'] or '', answer)
            sheet.write(row_no, 4, data['cash_collection'] or '', answer)
            sheet.write(row_no, 5, data['bank_deposit'] , answer)
            sheet.write(row_no, 6, data['closing_balance'] , answer)
            sheet.write(row_no, 7, data['uncleared_deposit'] , answer)
            row_no += 1
        fp = StringIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        return data
    
    @api.multi
    def bank_ledger_school_wise_detail_excel_report(self):
        if not self.from_data():
            raise ValidationError(_("No record found..!"))
        data = base64.encodestring(self.from_data())
        attach_vals = {
            'name':'%s.xls' % ('Cask Book School Wise'),
            'datas':data,
            'datas_fname':'%s.xls' % ('Cask Book School Wise'),
         }
        doc_id = self.env['ir.attachment'].create(attach_vals)
        return {
            'type': 'ir.actions.act_url',
            'url':'web/content/%s?download=true'%(doc_id.id),
            'target': 'self',
        }