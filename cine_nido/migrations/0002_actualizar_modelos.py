import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cine_nido", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="asiento",
            options={"ordering": ["sala", "fila", "numero"]},
        ),
        migrations.AlterModelOptions(
            name="compra",
            options={"ordering": ["-fecha_compra"]},
        ),
        migrations.RenameField(
            model_name="funcion",
            old_name="hora",
            new_name="fecha_hora",
        ),
        migrations.AlterModelOptions(
            name="funcion",
            options={"ordering": ["fecha_hora"]},
        ),
        migrations.RemoveField(
            model_name="funcion",
            name="horario",
        ),
        migrations.AddField(
            model_name="funcion",
            name="precio",
            field=models.PositiveIntegerField(default=5500),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pelicula",
            name="activa",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="pelicula",
            name="sinopsis",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="productoconfiteria",
            name="disponible",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="asiento",
            name="numero",
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name="asiento",
            name="sala",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="asientos",
                to="cine_nido.sala",
            ),
        ),
        migrations.AlterField(
            model_name="compra",
            name="total",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="compra",
            name="usuario",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="compras",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.DeleteModel(
            name="Usuario",
        ),
        migrations.AlterField(
            model_name="detalleconfiteria",
            name="cantidad",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name="detalleconfiteria",
            name="compra",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="detalles_confiteria",
                to="cine_nido.compra",
            ),
        ),
        migrations.AlterField(
            model_name="detalleconfiteria",
            name="precio_unitario",
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name="entrada",
            name="compra",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="entradas",
                to="cine_nido.compra",
            ),
        ),
        migrations.AlterField(
            model_name="entrada",
            name="funcion",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="entradas",
                to="cine_nido.funcion",
            ),
        ),
        migrations.AlterField(
            model_name="entrada",
            name="precio",
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name="funcion",
            name="pelicula",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="funciones",
                to="cine_nido.pelicula",
            ),
        ),
        migrations.AlterField(
            model_name="funcion",
            name="sala",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="funciones",
                to="cine_nido.sala",
            ),
        ),
        migrations.AlterField(
            model_name="pelicula",
            name="duracion",
            field=models.PositiveIntegerField(help_text="Duración en minutos"),
        ),
        migrations.AlterField(
            model_name="productoconfiteria",
            name="precio_unitario",
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name="sala",
            name="nombre_sala",
            field=models.CharField(max_length=50, unique=True),
        ),
        migrations.AddConstraint(
            model_name="asiento",
            constraint=models.UniqueConstraint(
                fields=("sala", "fila", "numero"), name="asiento_unico_por_sala"
            ),
        ),
        migrations.AddConstraint(
            model_name="entrada",
            constraint=models.UniqueConstraint(
                fields=("funcion", "asiento"), name="asiento_unico_por_funcion"
            ),
        ),
        migrations.AddConstraint(
            model_name="funcion",
            constraint=models.UniqueConstraint(
                fields=("sala", "fecha_hora"), name="funcion_unica_por_sala_y_hora"
            ),
        ),
    ]
