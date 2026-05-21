import json
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from .models import Pasajero


class PasajeroModelTests(TestCase):
    """Pruebas para el modelo Pasajero"""

    def setUp(self):
        """Crear un pasajero para pruebas"""
        self.pasajero = Pasajero.objects.create(
            dni='71852009',
            nombres='Juan',
            apellidos='Pérez García',
            genero='M',
            telefono='967271234',
            correo='juan@gmail.com'
        )

    def test_crear_pasajero(self):
        """Verificar que se crea un pasajero correctamente"""
        self.assertEqual(self.pasajero.dni, '71852009')
        self.assertEqual(self.pasajero.nombre_completo, 'Juan Pérez García')

    def test_dni_unico(self):
        """Verificar que DNI no puede duplicarse"""
        with self.assertRaises(Exception):
            Pasajero.objects.create(
                dni='71852009',  # DNI duplicado
                nombres='Otro',
                apellidos='Usuario'
            )

    def test_telefono_parcial(self):
        """Verificar ocultamiento de teléfono"""
        parcial = self.pasajero.telefonos_parcial()
        self.assertEqual(parcial, '967271XXX')
        self.assertNotIn('234', parcial)  # No debe mostrar últimos 3 dígitos

    def test_correo_parcial(self):
        """Verificar ocultamiento de correo"""
        parcial = self.pasajero.correo_parcial()
        self.assertEqual(parcial, 'jua****@gmail.com')
        self.assertNotIn('juan@', parcial.split('@')[0] + '@')  # Verificar ocultamiento

    def test_to_dict_oculto(self):
        """Verificar serialización con datos ocultos"""
        datos = self.pasajero.to_dict(incluir_completos=False)
        self.assertEqual(datos['telefono'], '967271XXX')
        self.assertEqual(datos['correo'], 'jua****@gmail.com')
        self.assertTrue(datos['existe'])

    def test_to_dict_completo(self):
        """Verificar serialización con datos completos"""
        datos = self.pasajero.to_dict(incluir_completos=True)
        self.assertEqual(datos['telefono'], '967271234')
        self.assertEqual(datos['correo'], 'juan@gmail.com')


class BuscarPasajeroAPITests(TestCase):
    """Pruebas para el endpoint de búsqueda"""

    def setUp(self):
        self.client = Client()
        self.pasajero = Pasajero.objects.create(
            dni='71852009',
            nombres='Juan',
            apellidos='Pérez García',
            telefono='967271234',
            correo='juan@gmail.com'
        )

    def test_buscar_pasajero_existente(self):
        """Verificar que encuentra un pasajero existente"""
        response = self.client.get(reverse('cuentas:buscar_pasajero_dni'), {
            'dni': '71852009'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['existe'])
        self.assertEqual(data['dni'], '71852009')
        self.assertEqual(data['nombres'], 'Juan')

    def test_buscar_pasajero_no_existe(self):
        """Verificar que retorna false si no existe"""
        response = self.client.get(reverse('cuentas:buscar_pasajero_dni'), {
            'dni': '99999999'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['existe'])

    def test_buscar_sin_dni(self):
        """Verificar que pide DNI"""
        response = self.client.get(reverse('cuentas:buscar_pasajero_dni'))
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_datos_ocultos_en_api(self):
        """Verificar que datos sensibles están ocultos"""
        response = self.client.get(reverse('cuentas:buscar_pasajero_dni'), {
            'dni': '71852009'
        })
        data = json.loads(response.content)
        # Teléfono debe estar oculto
        self.assertEqual(data['telefono'], '967271XXX')
        # Correo debe estar oculto
        self.assertNotEqual(data['correo'], 'juan@gmail.com')


class GuardarPasajeroAPITests(TestCase):
    """Pruebas para el endpoint de guardar/actualizar"""

    def setUp(self):
        self.client = Client()
        self.url = reverse('cuentas:guardar_pasajero')

    def test_crear_pasajero(self):
        """Verificar creación de nuevo pasajero"""
        response = self.client.post(
            self.url,
            data=json.dumps({
                'dni': '12345678',
                'nombres': 'María',
                'apellidos': 'Gonzales',
                'telefono': '912345678',
                'correo': 'maria@gmail.com'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertTrue(data['creado'])
        self.assertFalse(data['actualizado'])
        # Verificar que existe en base de datos
        self.assertTrue(Pasajero.objects.filter(dni='12345678').exists())

    def test_actualizar_pasajero(self):
        """Verificar actualización de pasajero existente"""
        pasajero = Pasajero.objects.create(
            dni='71852009',
            nombres='Juan',
            apellidos='Pérez',
            telefono='967271234',
            correo='juan@gmail.com'
        )
        # Actualizar teléfono
        response = self.client.post(
            self.url,
            data=json.dumps({
                'dni': '71852009',
                'nombres': 'Juan',
                'apellidos': 'Pérez',
                'telefono': '912345678',  # Teléfono diferente
                'correo': 'juan@gmail.com'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['creado'])
        self.assertTrue(data['actualizado'])
        # Verificar que se actualizó
        pasajero_actualizado = Pasajero.objects.get(dni='71852009')
        self.assertEqual(pasajero_actualizado.telefono, '912345678')

    def test_campos_obligatorios(self):
        """Verificar que pide campos obligatorios"""
        response = self.client.post(
            self.url,
            data=json.dumps({
                'dni': '71852009',
                # Falta 'nombres' y 'apellidos'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_dni_invalido(self):
        """Verificar validación de DNI"""
        # DNI vacío
        response = self.client.post(
            self.url,
            data=json.dumps({
                'dni': '',
                'nombres': 'Juan',
                'apellidos': 'Pérez'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_json_invalido(self):
        """Verificar manejo de JSON inválido"""
        response = self.client.post(
            self.url,
            data='JSON INVÁLIDO',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)


class ObtenerPasajeroAPITests(TestCase):
    """Pruebas para obtener datos completos (admin)"""

    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            email='admin@test.com',
            password='testpass123',
            nombres='Admin',
            apellidos='Sistema',
            dni='12345678',
        )
        self.pasajero = Pasajero.objects.create(
            dni='71852009',
            nombres='Juan',
            apellidos='Pérez',
            telefono='967271234',
            correo='juan@gmail.com'
        )

    def test_obtener_pasajero_existente(self):
        """Verificar obtención de pasajero"""
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('cuentas:obtener_pasajero', args=[self.pasajero.id])
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        # Datos completos sin ocultamiento
        self.assertEqual(data['telefono'], '967271234')
        self.assertEqual(data['correo'], 'juan@gmail.com')

    def test_obtener_pasajero_no_existe(self):
        """Verificar error si no existe"""
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('cuentas:obtener_pasajero', args=[9999])
        )
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_obtener_pasajero_requiere_staff(self):
        """No debe exponer datos completos a usuarios anonimos"""
        response = self.client.get(
            reverse('cuentas:obtener_pasajero', args=[self.pasajero.id])
        )
        self.assertEqual(response.status_code, 403)


class IntegracionBoletoTests(TestCase):
    """Pruebas de integración con Boleto (futuro)"""

    def test_guardar_pasajero_con_boleto(self):
        """
        Simular que al guardar un Boleto también
        se guarda el Pasajero automáticamente
        """
        # Este test requeriría la importación de Boleto
        # y una lógica de integración en models.py
        pass
