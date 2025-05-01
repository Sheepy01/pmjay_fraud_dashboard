import pandas as pd
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime
from pmjay_fraud_dashboard_app.models import (
    Last24Hour,
    SuspiciousHospital,
    HospitalBeds
)

class Command(BaseCommand):
    help = 'Import data from multiple Excel files into the database'

    def handle(self, *args, **kwargs):
        # -------------------------------------------------------------------
        # 1) Clear existing data to avoid duplicates (optional)
        # -------------------------------------------------------------------
        HospitalBeds.objects.all().delete()
        SuspiciousHospital.objects.all().delete()
        Last24Hour.objects.all().delete()

        # Import Hospital Beds data
        try:
            hb_df = pd.read_excel('data/HOSPITAL_BEDS.xlsx')
            hb_df.columns = hb_df.columns.str.strip()

            hb_instances = []
            for _, row in hb_df.iterrows():
                # Safely retrieve bed strength, defaulting to 0 if NaN
                bed_strength_val = row.get('Bed Strength', 0)
                if pd.isnull(bed_strength_val):
                    bed_strength_val = 0
                bed_strength = int(bed_strength_val)

                hospital_id = str(row['Hospital ID']).strip().upper()

                hb_instances.append(
                    HospitalBeds(
                        hospital_id=hospital_id,
                        bed_strength=bed_strength
                    )
                )
            HospitalBeds.objects.bulk_create(hb_instances, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS('Hospital Beds data imported successfully!'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('File data/HOSPITAL_BEDS.xlsx not found. Skipping HospitalBeds import.'))
        except KeyError as e:
            self.stdout.write(self.style.ERROR(f'Missing expected column in HOSPITAL_BEDS.xlsx: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing HospitalBeds: {e}'))

        # -------------------------------------------------------------------
        # 3) Import Suspicious Hospital data
        # -------------------------------------------------------------------
        try:
            sh_df = pd.read_excel('data/Suspicious_Hospital_List.xlsx')
            sh_df.columns = sh_df.columns.str.strip()

            sh_instances = []
            for _, row in sh_df.iterrows():
                sh_instances.append(
                    SuspiciousHospital(
                        hospital_id=str(row['Hospital Id']).strip().upper(),
                        hospital_name=str(row['Hospital Name']).strip(),
                        number_of_surgeons=row.get('Number of Surgeons', None),
                        number_of_ot=row.get('Number of OT', None)
                    )
                )
            SuspiciousHospital.objects.bulk_create(sh_instances, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS('Suspicious Hospital data imported successfully!'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('File data/Suspicious_Hospital_List.xlsx not found. Skipping SuspiciousHospital import.'))
        except KeyError as e:
            self.stdout.write(self.style.ERROR(f'Missing expected column in Suspicious_Hospital_List.xlsx: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing SuspiciousHospital: {e}'))

        # -------------------------------------------------------------------
        # 4) Import Last 24 Hours data (Dump sheet)
        # -------------------------------------------------------------------
        try:
            l24_df = pd.read_excel('data/Combined_Last24Hours.xlsx', sheet_name='Dump')
            l24_df.columns = l24_df.columns.str.strip()

            l24_instances = []
            for _, row in l24_df.iterrows():
                raw_date = str(row['Preauth Initiated Date'])
                parsed_date = parse_datetime(raw_date)
                # Convert to naive datetime if timezone-aware
                if parsed_date and parsed_date.tzinfo is not None:
                    parsed_date = parsed_date.replace(tzinfo=None)

                l24_instances.append(
                    Last24Hour(
                        hospital_id=str(row['Hospital Code']).strip().upper(),
                        hospital_type=str(row['Hospital Type']).strip(),
                        preauth_initiated_date=parsed_date,
                        case_type=str(row['Case Type']).strip(),
                        claim_initiated_amount=row['Claim Initiated Amount(Rs.)'],
                        state_name=str(row['State Name']).strip(),
                        age_years=str(row['Age(Years)']).strip(),
                        preauth_initiated_time = str(row['Preauth Initiated Time']).strip(),
                        procedure_code = str(row['Procedure Code']).strip(),
                        district_name = str(row['District Name']).strip(),
                        patient_name = str(row['Patient Name']).strip(),
                        registration_id = str(row['Registration Id']).strip(),
                        gender = str(row['Gender']).strip().upper(),
                        hospital_name = str(row['Hospital Name']).strip().upper(),
                        hospital_state_name = str(row['Hospital State Name']).strip().upper(),
                        family_id = str(row['Family Id']).strip(),
                    )
                )
            Last24Hour.objects.bulk_create(l24_instances, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS('Last 24 Hours data imported successfully!'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('File data/Last 24 Hours Bihar Reports 05-02-2025.xlsx not found. Skipping Last24Hour import.'))
        except KeyError as e:
            self.stdout.write(self.style.ERROR(f'Missing expected column in Last 24 Hours Bihar Reports 05-02-2025.xlsx: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing Last24Hour: {e}'))

        self.stdout.write(self.style.SUCCESS('All data imported successfully.'))