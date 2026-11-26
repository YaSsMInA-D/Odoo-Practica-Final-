from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import timedelta

class Prestamo(models.Model):
    _name = 'biblioteca.prestamo'
    _description = 'Préstamo de un libro'
    _order = 'fecha_prestamo desc, id desc'

    name = fields.Char(string='Referencia', required=True, copy=False, default='Nuevo')
    libro_id = fields.Many2one('biblioteca.libro', string='Libro', required=True, ondelete='restrict')
    
    # Note: the domain ensures only socios can be selected
    socio_id = fields.Many2one('res.partner', string='Socio', required=True, ondelete='restrict', domain=[('es_socio', '=', True)])
    
    fecha_prestamo = fields.Date(string='Fecha de préstamo', required=True, default=fields.Date.context_today)
    dias = fields.Integer(string='Días de préstamo', default=15)
    
    # Computed fields (Calculated automatically)
    fecha_devolucion = fields.Date(string='Fecha de devolución', compute='_compute_fecha_devolucion', store=True)
    retraso = fields.Boolean(string='Retrasado', compute='_compute_retraso', store=True)
    dias_retraso = fields.Integer(string='Días de retraso', compute='_compute_retraso', store=True)

    estado = fields.Selection([
        ('borrador', 'Borrador'),
        ('prestado', 'Prestado'),
        ('devuelto', 'Devuelto'),
    ], string='Estado', default='borrador', required=True)

    # 1. Automatic Sequence Generation
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('biblioteca.prestamo') or 'Nuevo'
        return super(Prestamo, self).create(vals_list)

    # 2. Calculate the return date
    @api.depends('fecha_prestamo', 'dias')
    def _compute_fecha_devolucion(self):
        for rec in self:
            if rec.fecha_prestamo and rec.dias:
                rec.fecha_devolucion = rec.fecha_prestamo + timedelta(days=rec.dias)
            else:
                rec.fecha_devolucion = False

    # 3. Calculate if it is late
    @api.depends('fecha_devolucion', 'estado')
    def _compute_retraso(self):
        hoy = fields.Date.context_today(self)
        for rec in self:
            if rec.estado == 'prestado' and rec.fecha_devolucion and rec.fecha_devolucion < hoy:
                rec.retraso = True
                rec.dias_retraso = (hoy - rec.fecha_devolucion).days
            else:
                rec.retraso = False
                rec.dias_retraso = 0

    # 4. Validation Constraint
    @api.constrains('dias')
    def _check_dias(self):
        for rec in self:
            if rec.dias <= 0:
                raise ValidationError("Los días de préstamo deben ser mayores que 0.")

    # 5. Buttons logic
    def action_prestar(self):
        for rec in self:
            if rec.libro_id.disponible:
                rec.estado = 'prestado'
                rec.libro_id.disponible = False
            else:
                raise ValidationError("El libro no está disponible.")

    def action_devolver(self):
        for rec in self:
            rec.estado = 'devuelto'
            rec.libro_id.disponible = True