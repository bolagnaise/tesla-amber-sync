# app/custom_tou_routes.py
"""Routes for custom TOU schedule management"""
from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import CustomTOUSchedule, TOUSeason, TOUPeriod
from app.forms import CustomTOUScheduleForm, TOUSeasonForm, TOUPeriodForm
from app.custom_tou_builder import CustomTOUBuilder
from app.api_clients import TeslemetryAPIClient
from app.utils import decrypt_token
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Create blueprint
custom_tou_bp = Blueprint('custom_tou', __name__, url_prefix='/custom-tou')


@custom_tou_bp.route('/')
@login_required
def index():
    """List all custom TOU schedules"""
    schedules = CustomTOUSchedule.query.filter_by(user_id=current_user.id).all()
    return render_template('custom_tou/index.html', schedules=schedules)


@custom_tou_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_schedule():
    """Create a new custom TOU schedule (wizard version)"""
    if request.method == 'POST':
        try:
            # Get form data
            utility = request.form.get('utility')
            name = request.form.get('name')
            code = request.form.get('code', '')
            daily_charge = float(request.form.get('daily_charge', 0))
            monthly_charge = float(request.form.get('monthly_charge', 0))
            set_active = bool(request.form.get('set_active'))
            seasons_json = request.form.get('seasons_data', '[]')

            # Validate required fields
            if not utility or not name:
                flash('Utility Provider and Rate Plan Name are required', 'danger')
                form = CustomTOUScheduleForm()
                return render_template('custom_tou/create_schedule_wizard.html', form=form)

            # Parse seasons data
            import json
            seasons_data = json.loads(seasons_json)

            if not seasons_data or len(seasons_data) == 0:
                flash('At least one season is required', 'danger')
                form = CustomTOUScheduleForm()
                return render_template('custom_tou/create_schedule_wizard.html', form=form)

            # Check if any season has periods
            total_periods = sum(len(s.get('periods', [])) for s in seasons_data)
            if total_periods == 0:
                flash('At least one time period is required', 'danger')
                form = CustomTOUScheduleForm()
                return render_template('custom_tou/create_schedule_wizard.html', form=form)

            # Deactivate other schedules if this will be active
            if set_active:
                CustomTOUSchedule.query.filter_by(
                    user_id=current_user.id,
                    active=True
                ).update({'active': False})

            # Create schedule
            schedule = CustomTOUSchedule(
                user_id=current_user.id,
                name=name,
                utility=utility,
                code=code,
                daily_charge=daily_charge,
                monthly_charge=monthly_charge,
                active=set_active
            )
            db.session.add(schedule)
            db.session.flush()  # Get schedule.id

            # Create seasons and periods
            for season_data in seasons_data:
                season = TOUSeason(
                    schedule_id=schedule.id,
                    name=season_data['name'],
                    from_month=season_data['from_month'],
                    from_day=season_data['from_day'],
                    to_month=season_data['to_month'],
                    to_day=season_data['to_day']
                )
                db.session.add(season)
                db.session.flush()  # Get season.id

                # Create periods for this season
                for i, period_data in enumerate(season_data.get('periods', [])):
                    period = TOUPeriod(
                        season_id=season.id,
                        name=period_data['name'],
                        from_hour=period_data['from_hour'],
                        from_minute=period_data['from_minute'],
                        to_hour=period_data['to_hour'],
                        to_minute=period_data['to_minute'],
                        from_day_of_week=period_data['from_day_of_week'],
                        to_day_of_week=period_data['to_day_of_week'],
                        energy_rate=period_data['energy_rate'],
                        sell_rate=period_data['sell_rate'],
                        demand_rate=period_data.get('demand_rate', 0),
                        display_order=i
                    )
                    db.session.add(period)

            db.session.commit()

            flash(f'✓ Created schedule "{schedule.name}" with {len(seasons_data)} season(s) and {total_periods} period(s)!', 'success')
            return redirect(url_for('custom_tou.preview_schedule', schedule_id=schedule.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating schedule: {e}", exc_info=True)
            flash(f'Error creating schedule: {str(e)}', 'danger')
            form = CustomTOUScheduleForm()
            return render_template('custom_tou/create_schedule_wizard.html', form=form)

    # GET request - show wizard
    # Create a form just for CSRF token
    form = CustomTOUScheduleForm()
    return render_template('custom_tou/create_schedule_wizard.html', form=form)


@custom_tou_bp.route('/edit/<int:schedule_id>', methods=['GET', 'POST'])
@login_required
def edit_schedule(schedule_id):
    """Edit a custom TOU schedule (uses same wizard as create)"""
    schedule = CustomTOUSchedule.query.get_or_404(schedule_id)

    # Check ownership
    if schedule.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('custom_tou.index'))

    if request.method == 'POST':
        try:
            # Get form data
            utility = request.form.get('utility')
            name = request.form.get('name')
            code = request.form.get('code', '')
            daily_charge = float(request.form.get('daily_charge', 0))
            monthly_charge = float(request.form.get('monthly_charge', 0))
            set_active = bool(request.form.get('set_active'))
            seasons_json = request.form.get('seasons_data', '[]')

            # Validate required fields
            if not utility or not name:
                flash('Utility Provider and Rate Plan Name are required', 'danger')
                form = CustomTOUScheduleForm()
                return render_template('custom_tou/create_schedule_wizard.html', form=form, schedule=schedule, edit_mode=True)

            # Parse seasons data
            import json
            seasons_data = json.loads(seasons_json)

            if not seasons_data or len(seasons_data) == 0:
                flash('At least one season is required', 'danger')
                form = CustomTOUScheduleForm()
                return render_template('custom_tou/create_schedule_wizard.html', form=form, schedule=schedule, edit_mode=True)

            # Check if any season has periods
            total_periods = sum(len(s.get('periods', [])) for s in seasons_data)
            if total_periods == 0:
                flash('At least one time period is required', 'danger')
                form = CustomTOUScheduleForm()
                return render_template('custom_tou/create_schedule_wizard.html', form=form, schedule=schedule, edit_mode=True)

            # Deactivate other schedules if this will be active
            if set_active and not schedule.active:
                CustomTOUSchedule.query.filter_by(
                    user_id=current_user.id,
                    active=True
                ).update({'active': False})

            # Update schedule
            schedule.name = name
            schedule.utility = utility
            schedule.code = code
            schedule.daily_charge = daily_charge
            schedule.monthly_charge = monthly_charge
            schedule.active = set_active
            schedule.updated_at = datetime.utcnow()

            # Delete existing seasons and periods (cascade will handle periods)
            TOUSeason.query.filter_by(schedule_id=schedule.id).delete()

            # Create new seasons and periods
            for season_data in seasons_data:
                season = TOUSeason(
                    schedule_id=schedule.id,
                    name=season_data['name'],
                    from_month=season_data['from_month'],
                    from_day=season_data['from_day'],
                    to_month=season_data['to_month'],
                    to_day=season_data['to_day']
                )
                db.session.add(season)
                db.session.flush()  # Get season.id

                # Create periods for this season
                for i, period_data in enumerate(season_data.get('periods', [])):
                    period = TOUPeriod(
                        season_id=season.id,
                        name=period_data['name'],
                        from_hour=period_data['from_hour'],
                        from_minute=period_data['from_minute'],
                        to_hour=period_data['to_hour'],
                        to_minute=period_data['to_minute'],
                        from_day_of_week=period_data['from_day_of_week'],
                        to_day_of_week=period_data['to_day_of_week'],
                        energy_rate=period_data['energy_rate'],
                        sell_rate=period_data['sell_rate'],
                        demand_rate=period_data.get('demand_rate', 0),
                        display_order=i
                    )
                    db.session.add(period)

            db.session.commit()

            flash(f'✓ Updated schedule "{schedule.name}" with {len(seasons_data)} season(s) and {total_periods} period(s)!', 'success')
            return redirect(url_for('custom_tou.index'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating schedule: {e}", exc_info=True)
            flash(f'Error updating schedule: {str(e)}', 'danger')
            form = CustomTOUScheduleForm()
            return render_template('custom_tou/create_schedule_wizard.html', form=form, schedule=schedule, edit_mode=True)

    # GET request - show wizard with existing data
    form = CustomTOUScheduleForm()
    return render_template('custom_tou/create_schedule_wizard.html', form=form, schedule=schedule, edit_mode=True)


@custom_tou_bp.route('/<int:schedule_id>/delete', methods=['POST'])
@login_required
def delete_schedule(schedule_id):
    """Delete a custom TOU schedule"""
    schedule = CustomTOUSchedule.query.get_or_404(schedule_id)

    if schedule.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('custom_tou.index'))

    db.session.delete(schedule)
    db.session.commit()

    flash(f'Deleted schedule "{schedule.name}"', 'success')
    return redirect(url_for('custom_tou.index'))


@custom_tou_bp.route('/<int:schedule_id>/activate', methods=['POST'])
@login_required
def activate_schedule(schedule_id):
    """Set a schedule as active (deactivates others)"""
    schedule = CustomTOUSchedule.query.get_or_404(schedule_id)

    if schedule.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('custom_tou.index'))

    # Deactivate all other schedules
    CustomTOUSchedule.query.filter_by(
        user_id=current_user.id,
        active=True
    ).update({'active': False})

    # Activate this schedule
    schedule.active = True
    db.session.commit()

    flash(f'Activated schedule "{schedule.name}"', 'success')
    return redirect(url_for('custom_tou.index'))


@custom_tou_bp.route('/<int:schedule_id>/season/add', methods=['GET', 'POST'])
@login_required
def add_season(schedule_id):
    """Add a season to a schedule"""
    schedule = CustomTOUSchedule.query.get_or_404(schedule_id)

    if schedule.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('custom_tou.index'))

    form = TOUSeasonForm()

    if form.validate_on_submit():
        season = TOUSeason(
            schedule_id=schedule.id,
            name=form.name.data,
            from_month=form.from_month.data,
            from_day=form.from_day.data,
            to_month=form.to_month.data,
            to_day=form.to_day.data
        )

        db.session.add(season)
        db.session.commit()

        flash(f'Added season "{season.name}"', 'success')
        return redirect(url_for('custom_tou.edit_schedule', schedule_id=schedule.id))

    return render_template('custom_tou/add_season.html', form=form, schedule=schedule)


@custom_tou_bp.route('/season/<int:season_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_season(season_id):
    """Edit a season"""
    season = TOUSeason.query.get_or_404(season_id)

    if season.schedule.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('custom_tou.index'))

    form = TOUSeasonForm(obj=season)

    if form.validate_on_submit():
        season.name = form.name.data
        season.from_month = form.from_month.data
        season.from_day = form.from_day.data
        season.to_month = form.to_month.data
        season.to_day = form.to_day.data

        db.session.commit()
        flash('Season updated', 'success')
        return redirect(url_for('custom_tou.edit_schedule', schedule_id=season.schedule_id))

    return render_template('custom_tou/edit_season.html', form=form, season=season)


@custom_tou_bp.route('/season/<int:season_id>/delete', methods=['POST'])
@login_required
def delete_season(season_id):
    """Delete a season"""
    season = TOUSeason.query.get_or_404(season_id)

    if season.schedule.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('custom_tou.index'))

    schedule_id = season.schedule_id
    db.session.delete(season)
    db.session.commit()

    flash(f'Deleted season "{season.name}"', 'success')
    return redirect(url_for('custom_tou.edit_schedule', schedule_id=schedule_id))


@custom_tou_bp.route('/season/<int:season_id>/period/add', methods=['GET', 'POST'])
@login_required
def add_period(season_id):
    """Add a time period to a season"""
    season = TOUSeason.query.get_or_404(season_id)

    if season.schedule.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('custom_tou.index'))

    form = TOUPeriodForm()

    if form.validate_on_submit():
        # Get the highest display_order and add 1
        max_order = db.session.query(db.func.max(TOUPeriod.display_order)).filter_by(
            season_id=season.id
        ).scalar() or 0

        period = TOUPeriod(
            season_id=season.id,
            name=form.name.data,
            from_hour=form.from_hour.data,
            from_minute=int(form.from_minute.data),
            to_hour=form.to_hour.data,
            to_minute=int(form.to_minute.data),
            from_day_of_week=int(form.from_day_of_week.data),
            to_day_of_week=int(form.to_day_of_week.data),
            energy_rate=form.energy_rate.data,
            sell_rate=form.sell_rate.data,
            demand_rate=form.demand_rate.data or 0,
            display_order=max_order + 1
        )

        db.session.add(period)
        db.session.commit()

        flash(f'Added period "{period.name}"', 'success')
        return redirect(url_for('custom_tou.edit_schedule', schedule_id=season.schedule_id))

    return render_template('custom_tou/add_period.html', form=form, season=season)


@custom_tou_bp.route('/period/<int:period_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_period(period_id):
    """Edit a time period"""
    period = TOUPeriod.query.get_or_404(period_id)

    if period.season.schedule.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('custom_tou.index'))

    form = TOUPeriodForm(obj=period)

    if form.validate_on_submit():
        period.name = form.name.data
        period.from_hour = form.from_hour.data
        period.from_minute = int(form.from_minute.data)
        period.to_hour = form.to_hour.data
        period.to_minute = int(form.to_minute.data)
        period.from_day_of_week = int(form.from_day_of_week.data)
        period.to_day_of_week = int(form.to_day_of_week.data)
        period.energy_rate = form.energy_rate.data
        period.sell_rate = form.sell_rate.data
        period.demand_rate = form.demand_rate.data or 0

        db.session.commit()
        flash('Period updated', 'success')
        return redirect(url_for('custom_tou.edit_schedule', schedule_id=period.season.schedule_id))

    # Pre-populate form with current values
    form.from_minute.data = str(period.from_minute)
    form.to_minute.data = str(period.to_minute)
    form.from_day_of_week.data = str(period.from_day_of_week)
    form.to_day_of_week.data = str(period.to_day_of_week)

    return render_template('custom_tou/edit_period.html', form=form, period=period)


@custom_tou_bp.route('/period/<int:period_id>/delete', methods=['POST'])
@login_required
def delete_period(period_id):
    """Delete a time period"""
    period = TOUPeriod.query.get_or_404(period_id)

    if period.season.schedule.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('custom_tou.index'))

    schedule_id = period.season.schedule_id
    db.session.delete(period)
    db.session.commit()

    flash(f'Deleted period "{period.name}"', 'success')
    return redirect(url_for('custom_tou.edit_schedule', schedule_id=schedule_id))


@custom_tou_bp.route('/<int:schedule_id>/preview')
@login_required
def preview_schedule(schedule_id):
    """Preview a schedule in Tesla tariff format"""
    schedule = CustomTOUSchedule.query.get_or_404(schedule_id)

    if schedule.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('custom_tou.index'))

    try:
        builder = CustomTOUBuilder()
        preview = builder.preview_schedule(schedule)
        tariff = builder.build_tesla_tariff(schedule)

        return render_template(
            'custom_tou/preview.html',
            schedule=schedule,
            preview=preview,
            tariff_json=tariff
        )
    except Exception as e:
        logger.error(f"Error previewing schedule: {e}", exc_info=True)
        flash(f'Error generating preview: {str(e)}', 'danger')
        return redirect(url_for('custom_tou.edit_schedule', schedule_id=schedule_id))


@custom_tou_bp.route('/<int:schedule_id>/sync', methods=['POST'])
@login_required
def sync_to_tesla(schedule_id):
    """Sync a custom TOU schedule to Tesla Powerwall"""
    schedule = CustomTOUSchedule.query.get_or_404(schedule_id)

    if schedule.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('custom_tou.index'))

    # Check if Tesla is configured
    if not current_user.tesla_energy_site_id:
        flash('Tesla Energy Site ID not configured. Please configure in Settings.', 'danger')
        return redirect(url_for('custom_tou.index'))

    try:
        # Build Tesla tariff
        builder = CustomTOUBuilder()
        tariff = builder.build_tesla_tariff(schedule)

        # Get Tesla API client
        tesla_client = None

        # Try Teslemetry API
        if current_user.teslemetry_api_key_encrypted:
            try:
                teslemetry_key = decrypt_token(current_user.teslemetry_api_key_encrypted)
                tesla_client = TeslemetryAPIClient(teslemetry_key)
                logger.info("Using Teslemetry client for custom TOU sync")
            except Exception as e:
                logger.error(f"Failed to initialize Teslemetry client: {e}")

        if not tesla_client:
            flash('Tesla API not configured. Please connect Tesla in Settings.', 'danger')
            return redirect(url_for('custom_tou.index'))

        # Send tariff to Tesla
        success = tesla_client.set_tariff_rate(current_user.tesla_energy_site_id, tariff)

        if success:
            schedule.last_synced = datetime.utcnow()
            db.session.commit()

            flash(f'Successfully synced "{schedule.name}" to Tesla!', 'success')
            logger.info(f"Successfully synced custom TOU schedule {schedule.id} to Tesla")
        else:
            flash('Failed to sync to Tesla. Check logs for details.', 'danger')
            logger.error(f"Failed to sync custom TOU schedule {schedule.id}")

    except Exception as e:
        logger.error(f"Error syncing schedule to Tesla: {e}", exc_info=True)
        flash(f'Error syncing to Tesla: {str(e)}', 'danger')

    return redirect(url_for('custom_tou.index'))
