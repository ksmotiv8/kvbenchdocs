/* ============================================
   Medical Corpus Generator — Blog Site Scripts
   ============================================ */

(function () {
    'use strict';

    /* --- Nav scroll effect --- */
    const nav = document.querySelector('nav');
    let lastScroll = 0;

    function handleScroll() {
        const scrollY = window.scrollY;
        if (scrollY > 40) {
            nav.classList.add('scrolled');
        } else {
            nav.classList.remove('scrolled');
        }
        lastScroll = scrollY;
    }

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();

    /* --- Theme toggle --- */
    const themeBtn = document.getElementById('theme-toggle');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');

    function getStoredTheme() {
        return localStorage.getItem('theme');
    }

    function setTheme(mode) {
        if (mode === 'light') {
            document.body.classList.add('light');
            themeBtn.textContent = '\u2600';
            themeBtn.setAttribute('aria-label', 'Switch to dark mode');
        } else {
            document.body.classList.remove('light');
            themeBtn.textContent = '\u263E';
            themeBtn.setAttribute('aria-label', 'Switch to light mode');
        }
        localStorage.setItem('theme', mode);
    }

    // Initialize theme
    const stored = getStoredTheme();
    if (stored) {
        setTheme(stored);
    } else {
        setTheme(prefersDark.matches ? 'dark' : 'dark'); // default dark
    }

    themeBtn.addEventListener('click', function () {
        const isLight = document.body.classList.contains('light');
        setTheme(isLight ? 'dark' : 'light');
    });

    /* --- Fade-up scroll animations --- */
    const fadeEls = document.querySelectorAll('.fade-up');

    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.08,
            rootMargin: '0px 0px -40px 0px'
        });

        fadeEls.forEach(function (el) {
            observer.observe(el);
        });
    } else {
        // Fallback: just show everything
        fadeEls.forEach(function (el) {
            el.classList.add('visible');
        });
    }

    /* --- Smooth scroll for nav links --- */
    document.querySelectorAll('a[href^="#"]').forEach(function (link) {
        link.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href === '#') return;
            const target = document.querySelector(href);
            if (target) {
                e.preventDefault();
                const offset = 80; // nav height + padding
                const top = target.getBoundingClientRect().top + window.scrollY - offset;
                window.scrollTo({ top: top, behavior: 'smooth' });
                // Close mobile nav if open
                closeMobileNav();
            }
        });
    });

    /* --- Mobile nav --- */
    const hamburger = document.getElementById('hamburger');
    const mobileNav = document.getElementById('mobile-nav');

    function closeMobileNav() {
        if (mobileNav) {
            mobileNav.classList.remove('open');
        }
    }

    if (hamburger && mobileNav) {
        hamburger.addEventListener('click', function () {
            mobileNav.classList.toggle('open');
        });
    }

    /* --- Active nav link highlighting --- */
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-links a[href^="#"]');

    function updateActiveLink() {
        const scrollY = window.scrollY + 120;
        let currentId = '';

        sections.forEach(function (section) {
            if (scrollY >= section.offsetTop) {
                currentId = section.id;
            }
        });

        navLinks.forEach(function (link) {
            link.style.color = '';
            if (link.getAttribute('href') === '#' + currentId) {
                link.style.color = 'var(--text-primary)';
            }
        });
    }

    window.addEventListener('scroll', updateActiveLink, { passive: true });
    updateActiveLink();

    /* --- Document Preview --- */
    var docPreviews = [
        {
            id: 'ed-note',
            label: 'ED Note',
            badge: 'Emergency',
            badgeClass: 'emergency',
            content: "**ED Note**\n\n**Patient Name:** James M. Harper  \n**Medical Record Number (MRN):** 123456789  \n**Date of Birth:** 06/15/1982  \n**Age:** 41 years  \n**Gender:** Male  \n**Race/Ethnicity:** White  \n**Primary Language:** English  \n**Marital Status:** Married  \n**Occupation:** Electrical Engineer  \n**Height:** 6'1\" (185 cm)  \n**Weight:** 210 lbs (95 kg)  \n**Blood Pressure:** 162/98 mmHg  \n**Heart Rate:** 110 bpm  \n**Respiratory Rate:** 22 breaths/min  \n**Temperature:** 99.6\u00b0F (37.5\u00b0C)  \n**SpO2:** 94% on room air  \n**Glasgow Coma Scale:** 15  \n**Pain Score (NRS):** 7/10  \n\n**Chief Complaint:**  \n\"Severe left upper quadrant abdominal pain for 12 hours, worsening over the past 4 hours, associated with nausea, vomiting, and intermittent diaphoresis.\"\n\n**Presenting History:**  \nThe patient is a 41-year-old male who presented to the Emergency Department after experiencing severe left upper quadrant abdominal pain that began 12 hours ago. The pain has progressively worsened over the past 4 hours and is now described as \"sharp and stabbing,\" with a sensation of fullness and bloating. He reports that the pain is constant, radiating to his left shoulder and back. The patient also reports nausea, with two episodes of non-bloody, non-bile-colored emesis approximately 2 hours apart. He denies any hematemesis, melena, or hematochezia. The pain is exacerbated by movement and deep breathing. He has not had any relief from over-the-counter medications, including acetaminophen and ibuprofen.\n\n**Past Medical History:**  \n- Hypertension (HTN) \u2013 managed with lisinopril 10 mg daily  \n- Hyperlipidemia \u2013 managed with atorvastatin 20 mg daily  \n- History of migraines \u2013 managed with topiramate 100 mg daily  \n- History of gastroesophageal reflux disease (GERD) \u2013 managed with omeprazole 20 mg daily  \n- History of hypothyroidism \u2013 managed with levothyroxine 100 mcg daily  \n- History of recurrent urinary tract infections (UTIs)  \n- No history of diabetes mellitus, asthma, or COPD  \n- No known drug allergies  \n\n**Family History:**  \n- Father: Died of complications of coronary artery disease at age 62  \n- Mother: Alive, 70 years old, with a history of hypertension and type 2 diabetes  \n- Siblings: One brother, 43 years old, with hypertension and hyperlipidemia  \n\n**Review of Systems:**  \n**Cardiovascular:** No chest pain, palpitations, or syncope.  \n**Respiratory:** No cough, dyspnea, or hemoptysis.  \n**Gastrointestinal:** Severe left upper quadrant pain, nausea, vomiting, and intermittent diaphoresis.  \n**Genitourinary:** No dysuria, hematuria, or flank pain.  \n**Neurological:** Alert and oriented \u00d73, no focal neurological deficits.  \n\n**Physical Examination:**  \n**VS:**  \n- Blood Pressure: 162/98 mmHg  \n- Heart Rate: 110 bpm  \n- Respiratory Rate: 22 breaths/min  \n- Temperature: 99.6\u00b0F (37.5\u00b0C)  \n- SpO2: 94% on room air  \n\n**General Appearance:**  \n- Alert, oriented \u00d73, in no acute distress, but appears uncomfortable due to pain.  \n- Skin color: pale, with no cyanosis or jaundice.  \n\n**Abdomen:**  \n- Distended, with tenderness localized to the left upper quadrant.  \n- No guarding or rigidity.  \n- No rebound tenderness.  \n- Bowel sounds are hypoactive.  \n- No peritoneal signs.  \n\n**Neurological:**  \n- Alert and oriented.  \n- No focal neurological deficits.  \n\n**Skin:**  "
        },
        {
            id: 'discharge-summary',
            label: 'Discharge Summary',
            badge: 'Emergency',
            badgeClass: 'emergency',
            content: "**DISCHARGE SUMMARY**  \n**Facility:** Jefferson Regional Medical Center  \n**Department:** Emergency Department  \n**Date of Discharge:** April 5, 2025  \n**Time of Discharge:** 10:15 AM  \n**Attending Physician:** Dr. Elena Martinez, MD  \n**Primary Care Physician:** Dr. Samuel Lin, MD  \n**Patient Name:** James Arthur Thompson  \n**Medical Record Number:** 123456789  \n**Date of Birth:** April 12, 1978  \n**Age:** 46 years  \n**Gender:** Male  \n**Weight:** 195 lbs (88.4 kg)  \n**Height:** 6'1\" (185.4 cm)  \n**Admission Date:** April 5, 2025  \n**Admission Type:** Emergency Department (ED) Discharge  \n\n---\n\n### **HISTORY OF PRESENT ILLNESS**  \nPatient is a 46-year-old male who presented to the Emergency Department via ambulance with a 2-hour history of acute chest pain radiating to the left arm, associated with diaphoresis, nausea, and dyspnea. The patient described the chest discomfort as a crushing, pressure-like sensation, with a rating of 8/10 on the visual analog scale. The pain began while he was working on a home computer late at night and was not relieved by rest or nitroglycerin.\n\n**PAST MEDICAL HISTORY**  \n- **Hypertension:** Controlled on Lisinopril 10 mg daily.  \n- **Hyperlipidemia:** Managed with Atorvastatin 40 mg daily.  \n- **Type 2 Diabetes Mellitus:** Managed with Metformin 500 mg twice daily.  \n- **Smoking History:** 20-pack-year smoker, currently attempting to quit.  \n- **Allergies:** No known drug allergies.  \n\n**PHYSICAL EXAMINATION**  \n**Vital Signs on Admission:**  \n- **Blood Pressure:** 130/85 mmHg  \n- **Heart Rate:** 108 bpm  \n- **Respiratory Rate:** 24 breaths per minute  \n- **Temperature:** 98.6\u00b0F (37.0\u00b0C)  \n- **Oxygen Saturation:** 98% on room air  \n\n**General Appearance:** Alert, oriented, and in acute distress. Appears anxious.  \n**Cardiovascular:** Regular rate and rhythm, 108 bpm. No murmurs, rubs, or gallops.  \n**Respiratory:** Clear to auscultation bilaterally.  \n\n---\n\n### **LABORATORY STUDIES**  \n**Complete Blood Count (CBC):**  \n- **Hemoglobin:** 14.2 g/dL  \n- **Hematocrit:** 42%  \n- **White Blood Cells (WBC):** 9.8 \u00d7 10\u00b3/\u03bcL  \n- **Platelets:** 215 \u00d7 10\u00b3/\u03bcL  \n\n**Basic Metabolic Panel (BMP):**  \n- **Sodium:** 140 mEq/L  \n- **Potassium:** 4.1 mEq/L  \n- **Chloride:** 102 mEq/L  \n- **Glucose:** 128 mg/dL  \n- **BUN:** 15 mg/dL  \n- **Creatinine:** 0.9 mg/dL  \n\n**Troponin I:**  \n- **Initial Troponin I (Admission):** 0.5 ng/mL  \n- **Repeat Troponin I (6 hours post-admission):** 0.7 ng/mL  \n- **Troponin I (12 hours post-admission):** 0.4 ng/mL  \n\n**Electrocardiogram (ECG):** Sinus tachycardia, non-specific ST-T changes, no acute ST elevation.  \n**Chest CT (Non-Contrast):** No evidence of acute pulmonary embolism."
        },
        {
            id: 'progress-note-1',
            label: 'Progress Note #1',
            badge: 'Inpatient',
            badgeClass: 'inpatient',
            content: "**Progress Note**  \n**Facility:** Jefferson General Hospital  \n**Service:** Internal Medicine  \n**Date:** April 5, 2025  \n**Time:** 10:30 AM  \n**Attending Physician:** Dr. Emily R. Carter, MD  \n**Resident:** Dr. Daniel M. Patel, MD  \n**Patient Name:** James W. Thompson  \n**Medical Record Number:** 456789  \n**Admission Date:** April 2, 2025  \n**Admitting Diagnosis:** Acute Renal Failure, Secondary to Acute Pyelonephritis  \n**Current Diagnosis:**  \n- Acute Renal Failure (ARF), secondary to acute pyelonephritis  \n- Hypertension, stage 2  \n- Type 2 Diabetes Mellitus, controlled  \n- Prostatic Hypertrophy with Urinary Retention  \n- Mild Aortic Stenosis  \n\n---\n\n**HISTORY OF PRESENT ILLNESS:**  \nThe patient, a 62-year-old white male, was admitted on April 2, 2025, via the Emergency Department (ED) following a 3-day history of worsening dysuria, urgency, suprapubic discomfort, and intermittent flank pain. On admission, the patient reported a 7-day history of fever (up to 101.2\u00b0F), chills, and malaise.\n\n**PAST MEDICAL HISTORY:**  \n- Hypertension, stage 2, treated with lisinopril and amlodipine  \n- Type 2 Diabetes Mellitus, controlled  \n- Hypothyroidism, well-controlled with levothyroxine 100 mcg daily  \n- Myocardial Infarction, April 2019  \n- Chronic Kidney Disease (CKD), stage 3, with baseline eGFR of 55 mL/min/1.73m\u00b2  \n- Benign Prostatic Hyperplasia (BPH), chronic urinary retention  \n\n**ALLERGIES:**  \n- Penicillin \u2013 Mild rash  \n\n**PHYSICAL EXAMINATION:**  \n**Vital Signs:**  \n- Temperature: 99.1\u00b0F (37.3\u00b0C)  \n- Pulse: 82 bpm  \n- Respiratory Rate: 16 breaths/min  \n- Blood Pressure: 142/86 mmHg  \n- Oxygen Saturation: 98% on room air  \n- Weight: 82 kg  \n- BMI: 27.5 kg/m\u00b2 (Overweight)  \n- Pain: 3/10 on visual analog scale (VAS)  \n\n**Chest:**  \n- Lungs: Clear to auscultation bilaterally.  \n- Heart: S1 and S2 normal. No murmur.  \n- Abdomen: Soft, nontender, non-distended.  \n\n**Genitourinary:**  \n- Prostate: Mildly enlarged, non-tender.  \n- Urinalysis: Positive for leukocyte esterase, nitrites, 3+ bacteria, 10\u201315 RBCs/hpf, 3+ protein.  \n\n**LABORATORY DATA (April 5, 2025):**  \n- **Creatinine:** 2.1 mg/dL (baseline 1.4 mg/dL)  \n- **BUN:** 26 mg/dL  \n- **eGFR:** 38 mL/min/1.73m\u00b2 (Stage 3 CKD)  \n- **CBC:**  \n  - WBC: 12.5 x10^9/L  \n  - Hemoglobin: 13.8 g/dL  \n  - Hematocrit: 41%  "
        },
        {
            id: 'progress-note-2',
            label: 'Progress Note #2',
            badge: 'Inpatient',
            badgeClass: 'inpatient',
            content: "**Progress Note**  \n**Facility:** Greenfield Regional Medical Center  \n**Department:** Inpatient Medicine  \n**Attending Physician:** Dr. Evelyn A. Mitchell, MD  \n**Resident:** Dr. Jordan T. Lee, MD  \n**Date:** April 5, 2025  \n**Time:** 09:30 AM  \n**Patient Name:** James Carter  \n**Medical Record Number:** 456789  \n**Admission Date:** April 3, 2025  \n**Admitting Diagnosis:** Acute Pancreatitis (suspected)  \n**Primary Diagnosis:** Acute Pancreatitis  \n**Secondary Diagnosis:** Hypertension, controlled  \n**Progress Note #4**  \n\n---\n\n**Patient Name:** James Carter  \n**Age:** 58  \n**Sex:** Male  \n**BMI:** 31.8 (Obese)  \n**Primary Insurance:** Blue Cross Blue Shield  \n**Allergies:** Penicillin (mild rash), Sulfa (severe anaphylaxis)  \n**Medications:**\n\n- Metoprolol 25 mg PO BID  \n- Lisinopril 10 mg PO QD  \n- Aspirin 81 mg PO QD  \n- Omeprazole 20 mg PO QD  \n- Ondansetron 4 mg PO QD  \n- Hydromorphone 2 mg PO PRN for pain  \n- Metoclopramide 10 mg PO QID  \n- IV fluids: Normal Saline 100 mL/hr  \n- Insulin glargine 10 units subQ QHS  \n- Simvastatin 20 mg PO QHS  \n\n**Vital Signs (April 5, 2025 @ 09:30 AM):**  \n- Temperature: 98.6\u00b0F (37.0\u00b0C)  \n- Pulse: 88 bpm  \n- Respiratory Rate: 16 breaths/min  \n- Blood Pressure: 138/86 mmHg  \n- Oxygen Saturation: 96% on room air  \n- Pain: 3/10 (abdominal)  \n- GCS: 15 (alert, oriented x3)  \n\n**Physical Examination:**\n\n**General:** Patient is alert, oriented to person, place, and time. No acute distress. Mild diaphoresis noted.  \n\n**Abdomen:** Scaphoid abdomen. Mild epigastric tenderness to palpation. No guarding or rigidity. No rebound tenderness. Bowel sounds are present in all quadrants.  \n\n**History of Present Illness:**  \nThe patient is a 58-year-old male with a history of hypertension, hyperlipidemia, and type 2 diabetes mellitus. He presented to the emergency department with a 2-day history of severe epigastric pain that has progressively worsened, accompanied by nausea, vomiting, and abdominal distension. On initial evaluation, he was found to have elevated serum lipase and amylase levels, along with elevated CRP and WBC count. CT scan showed signs of acute pancreatitis with mild edema and no evidence of necrosis.\n\n**Admission Plan:**  \n- Monitor for progression of pancreatitis  \n- Continue IV fluids to maintain hydration  \n- Continue pain management with hydromorphone PRN  \n- Monitor laboratory values: lipase, amylase, CBC, LFTs, renal function, and glucose  "
        },
        {
            id: 'med-recon',
            label: 'Med Reconciliation',
            badge: 'Inpatient',
            badgeClass: 'inpatient',
            content: "**Medication Reconciliation Report**  \n**Facility:** St. Mary's Regional Medical Center  \n**Department:** Inpatient Pharmacy and Medication Management  \n**Date:** April 5, 2025  \n**Time:** 10:15 AM  \n**Patient Name:** James T. Whitaker  \n**MRN:** 123456789  \n**Room:** 3 West  \n**Bed Number:** 314  \n**Admission Date:** April 3, 2025  \n**Admitting Service:** Internal Medicine  \n**Attending Physician:** Dr. Emily L. Chen, MD  \n**Reconciliation Type:** Initial Medication Reconciliation  \n**Status:** Complete  \n\n---\n\n### **I. Patient Demographics**\n\n**Name:** James T. Whitaker  \n**Date of Birth:** March 2, 1968  \n**Gender:** Male  \n**Race:** Caucasian  \n**Marital Status:** Married  \n**Occupation:** Retired High School Teacher  \n\n---\n\n### **II. Reason for Medication Reconciliation**\n\nThis medication reconciliation was conducted as part of the initial inpatient admission process for James T. Whitaker, a 57-year-old male admitted for evaluation and management of acute chest pain, suspected acute coronary syndrome (ACS).\n\n---\n\n### **III. Patient History**\n\n**Medical History:**\n\n- **Hypertension** \u2013 Diagnosed 10 years ago  \n- **Hyperlipidemia** \u2013 Diagnosed 8 years ago  \n- **Type 2 Diabetes Mellitus (T2DM)** \u2013 Diagnosed 6 years ago  \n- **Atrial Fibrillation (AFib)** \u2013 Diagnosed 4 years ago  \n- **GERD** \u2013 Diagnosed 3 years ago  \n- **Osteoarthritis of the knees** \u2013 Diagnosed 15 years ago  \n- **COPD** \u2013 Diagnosed 10 years ago  \n- **History of DVT** \u2013 2018, resolved  \n- **History of Colorectal Cancer** \u2013 2019, stage II  \n\n**Current Medications (Outpatient):**\n\n1. **Metformin Hydrochloride 500 mg BID**\n2. **Lisinopril 10 mg QD**\n3. **Simvastatin 20 mg QD**\n4. **Warfarin 5 mg QD**\n5. **Digoxin 0.125 mg QD**\n6. **Omeprazole 20 mg QD**\n7. **Ibuprofen 400 mg PRN**\n8. **Albuterol 2.5 mg/2.5 mL inhaler PRN**\n9. **Fluticasone 50 mcg/100 mcg inhaler BID**\n10. **Celecoxib 200 mg QD**\n11. **Duloxetine 60 mg QD**\n12. **Aspirin 81 mg QD**\n13. **Clopidogrel 75 mg QD**\n14. **Furosemide 40 mg QD**\n\n---\n\n### **IV. Inpatient Admission Findings**\n\n**Chief Complaint:**  \nChest pain, pressure, and shortness of breath (SOB) for 3 hours prior to admission.\n\n**Vital Signs at Admission:**\n\n- **Temperature:** 98.6\u00b0F (37.0\u00b0C)\n- **Pulse:** 108 bpm\n- **Respiratory Rate:** 22 breaths/min\n- **Blood Pressure:** 160/94 mmHg\n- **Oxygen Saturation:** 92% on room air\n- **Weight:** 190 lbs (86 kg)  "
        },
        {
            id: 'outpatient-note',
            label: 'Outpatient Note',
            badge: 'Outpatient',
            badgeClass: 'outpatient',
            content: "**Progress Note**  \n**Facility:** Green Valley Medical Center  \n**Department:** Outpatient Internal Medicine  \n**Date:** April 5, 2025  \n**Time:** 10:15 AM  \n**Attending Physician:** Dr. Emily A. Carter, MD  \n**Patient Name:** James T. Reynolds  \n**Medical Record Number:** 123456789  \n**Date of Birth:** April 12, 1965  \n**Gender:** Male  \n**Occupation:** Retired Firefighter  \n**Visit Type:** Follow-Up  \n**Reason for Visit:** Follow-up for hypertension, hyperlipidemia, and type 2 diabetes mellitus; review of medication adherence and lifestyle modifications  \n\n---\n\n**Chief Complaint:**  \nThe patient presents for a follow-up visit to monitor his chronic medical conditions and assess the effectiveness of his current treatment regimen. He reports no new or worsening symptoms but has been concerned about his recent fatigue and occasional dizziness.\n\n**History of Present Illness (HPI):**  \nThe patient is a 59-year-old male with a history of hypertension, hyperlipidemia, type 2 diabetes mellitus, and a recent history of a minor fall at home. He has been adherent to his medication regimen and has been following a low-sodium, low-fat, and low-sugar diet. He reports occasional fatigue that has been present for the past 2 months and occasional dizziness that occurs when standing up from a seated position.\n\n**Past Medical History (PMH):**  \n- Hypertension (HTN) \u2013 diagnosed 7 years ago  \n- Hyperlipidemia \u2013 diagnosed 5 years ago  \n- Type 2 Diabetes Mellitus (T2DM) \u2013 diagnosed 3 years ago  \n- Hypothyroidism \u2013 diagnosed 10 years ago  \n- Chronic lower back pain  \n- GERD  \n\n**Physical Examination:**  \n**Vital Signs:**  \n- Blood Pressure (BP): 138/86 mmHg  \n- Pulse: 76 bpm  \n- Respiratory Rate: 16 breaths/min  \n- Temperature: 98.4\u00b0F (36.9\u00b0C)  \n- Oxygen Saturation: 98% on room air  \n- Weight: 185 lbs (84 kg)  \n- Height: 5'10\" (178 cm)  \n- BMI: 27.5 (overweight)  \n- Blood Glucose: 132 mg/dL (fasting)  \n\n**General Appearance:**  \nThe patient is alert, oriented, and in no acute distress. Gait is steady.  \n\n**Laboratory Results:**  \n**Hemoglobin A1c (HbA1c):** 7.2% (target <7.0%)  \n**Total Cholesterol:** 225 mg/dL (LDL: 145 mg/dL, HDL: 45 mg/dL, Triglycerides: 180 mg/dL)  \n**Creatinine:** 1.1 mg/dL  \n**eGFR:** 78 mL/min/1.73m\u00b2  \n**Hemoglobin (Hb):** 14.2 g/dL  \n**WBC Count:** 8.2 x 10\u00b3/\u00b5L  \n**Platelet Count:** 210,000/\u00b5L  "
        },
        {
            id: 'preop-note',
            label: 'Preop Note',
            badge: 'Surgical',
            badgeClass: 'surgical',
            content: "**Preoperative Note**  \n**Patient Name:** Josephine \"Joey\" Martinez  \n**Medical Record Number:** 10245689  \n**Date of Birth:** 10/15/1982  \n**Age:** 41  \n**Gender:** Female  \n**Marital Status:** Married  \n**Occupation:** Office Manager  \n**Procedure Scheduled:** Laparoscopic Cholecystectomy  \n**Date of Surgery:** 12/10/2024  \n**Estimated Duration of Surgery:** 1.5 to 2 hours  \n**Anesthesia:** General Anesthesia (Propofol, Fentanyl, Rocuronium, Sevoflurane)  \n**Surgeon:** Dr. Lisa Nguyen, MD  \n\n---\n\n### **2. History of Present Illness (HPI)**\n\nPatient presents with a 3-week history of right upper quadrant (RUQ) abdominal pain, which is intermittent and colicky in nature, localized to the right hypochondrium. The pain is often exacerbated by fatty meals and is associated with occasional nausea but no vomiting. Patient reports that the pain has worsened over the past 7 days.\n\n### **3. Past Medical History (PMH)**\n\n- **Hypertension** \u2013 Diagnosed at age 35, managed with lisinopril 10 mg daily.  \n- **Hyperlipidemia** \u2013 Managed with atorvastatin 20 mg daily.  \n- **Type 2 Diabetes Mellitus** \u2013 Managed with metformin 500 mg twice daily and insulin glargine 10 units at bedtime.  \n- **Mild Asthma** \u2013 Controlled with albuterol inhaler as needed.  \n- **History of Appendectomy** \u2013 Age 22, uncomplicated.  \n\n### **7. Physical Examination**\n\n**Vital Signs (per admission):**  \n- **Temperature:** 98.6\u00b0F (37.0\u00b0C)  \n- **Pulse:** 82 bpm  \n- **Respirations:** 16 breaths/min  \n- **Blood Pressure:** 132/84 mmHg  \n- **Oxygen Saturation (on room air):** 98%  \n- **Height:** 5'5\" (165 cm)  \n- **Weight:** 142 lbs (64.4 kg)  \n- **Body Mass Index (BMI):** 23.7 kg/m\u00b2  \n\n**General Appearance:** Alert, oriented \u00d73, in no acute distress.  \n\n**Abdomen:**  \n- RUQ tenderness with guarding, no rebound tenderness.  \n- Liver: Slightly enlarged, no tenderness.  \n- Bowel Sounds: Normal, 10\u201312 per minute.  "
        },
        {
            id: 'imaging-report',
            label: 'Imaging Report',
            badge: 'Diagnostics',
            badgeClass: 'diagnostics',
            content: "**IMAGING REPORT**  \n**Facility:** Green Valley Regional Hospital  \n**Department:** Radiology  \n**Date of Report:** April 5, 2025  \n**Radiologist:** Dr. Eleanor S. Mitchell, MD, FACR  \n**Patient Name:** David A. Thompson  \n**MRN:** 123456789  \n**DOB:** 03/20/1972  \n**Age:** 53  \n**Gender:** Male  \n**Height:** 6'1\" (185 cm)  \n**Weight:** 200 lbs (90.7 kg)  \n**Reason for Exam:** Evaluation of persistent right upper quadrant (RUQ) pain, suspected cholelithiasis and possible gallbladder dysfunction  \n**Procedure:** Abdominal Ultrasound (US) with Doppler, followed by Contrast-Enhanced CT of the abdomen and pelvis  \n\n---\n\n### **1. Patient History and Clinical Context**\n\n**Past Medical History:**  \n- Hypertension (Stage 1), managed with Amlodipine 5 mg daily  \n- Hyperlipidemia (LDL 140 mg/dL, HDL 45 mg/dL, triglycerides 180 mg/dL)  \n- Type 2 Diabetes Mellitus (T2DM), controlled with Metformin 500 mg BID and Glimepiride 1 mg daily  \n- History of gastritis, managed with Omeprazole 20 mg daily  \n\n**Current Symptoms:**  \n- Persistent RUQ pain for 6 weeks  \n- Pain radiating to the right shoulder (referred pain)  \n- No nausea, vomiting, or jaundice  \n- Appetite decreased  \n\n---\n\n### **2. Radiological Examination**\n\n#### **2.1. Abdominal Ultrasound (April 4, 2025)**\n\n**Equipment Used:** Philips EPIQ 5 ultrasound machine  \n\n**Findings:**  \n- **Liver:** Size within normal limits. No focal lesions or masses. No steatosis or fibrosis.  \n- **Gallbladder:**  \n  - Size: Normal (2.8 cm in longitudinal axis)  \n  - Wall thickness: 3 mm, within normal limits  \n  - CBD diameter: 4 mm  \n  - No dilation of the CBD or intrahepatic bile ducts  \n  - No evidence of stones  \n  - Suggestive of impaired gallbladder motility  \n- **Pancreas:** Size within normal limits. No pancreatitis or mass.  \n- **Spleen and Kidneys:** Normal size and structure.  \n\n**Impression:**  \n- Inconclusive for cholelithiasis or acute cholecystitis  \n- Possible gallbladder dyskinesia  \n- Recommend further imaging (CT)  \n\n---\n\n#### **2.2. Contrast-Enhanced CT of the Abdomen and Pelvis (April 5, 2025)**\n\n**Equipment Used:**  "
        },
        {
            id: 'lab-report',
            label: 'Lab Report',
            badge: 'Diagnostics',
            badgeClass: 'diagnostics',
            content: "**LABORATORY REPORT**  \n**Patient ID:** 123456789  \n**Report Date:** April 15, 2025  \n**Facility:** Evergreen Regional Medical Center \u2013 Laboratory Services  \n**Department:** Clinical Laboratory  \n**Report Type:** CBC, CMP, Lipid Panel, Thyroid Function Test, Urinalysis, and HIV/HSV-2 Serology  \n\n---\n\n### **1. PATIENT INFORMATION**\n\n**Name:** Emily Grace Morgan  \n**Gender:** Female  \n**Date of Birth:** May 3, 1992  \n**Age:** 33  \n**Primary Physician:** Dr. Samuel K. Patel, MD  \n**Allergies:** Penicillin (mild rash)  \n**Medications:**  \n- Metformin 500 mg twice daily  \n- Lisinopril 10 mg once daily  \n- Atorvastatin 20 mg once daily  \n- Sertraline 50 mg once daily  \n- Omeprazole 20 mg once daily  \n- Furosemide 40 mg once daily  \n\n---\n\n### **3. VITAL SIGNS (AT TIME OF COLLECTION)**\n\n- **Temperature:** 98.6\u00b0F (37.0\u00b0C)  \n- **Pulse:** 78 bpm  \n- **Blood Pressure:** 132/84 mmHg  \n- **Oxygen Saturation (SpO\u2082):** 98% on room air  \n- **Height:** 5'5\" (165 cm)  \n- **Weight:** 148 lbs (67.1 kg)  \n- **BMI:** 23.4 kg/m\u00b2  \n\n---\n\n### **4. LABORATORY FINDINGS**\n\n#### **4.1 COMPLETED BLOOD COUNT (CBC)**\n\n| Parameter | Value | Reference Range | Interpretation |\n|----------|-------|------------------|----------------|\n| WBC | 8.2 x 10\u2079/L | 4.0\u201311.0 | Normal |\n| RBC | 4.5 x 10\u00b9\u00b2/L | 4.0\u20135.5 | Normal |\n| Hemoglobin | 13.8 g/dL | 12.0\u201315.5 | Normal |\n| Hematocrit | 39.8% | 37.0\u201347.0 | Normal |\n| Platelets | 225 x 10\u2079/L | 150\u2013450 | Normal |\n| Neutrophils | 52.3% | 40\u201375% | Normal |\n| Lymphocytes | 36.5% | 20\u201350% | Normal |\n\n#### **4.2 COMPREHENSIVE METABOLIC PANEL (CMP)**\n\n| Parameter | Value | Reference Range | Interpretation |\n|----------|-------|------------------|----------------|\n| Sodium | 138 mmol/L | 135\u2013145 | Normal |\n| Potassium | 4.1 mmol/L | 3.5\u20135.0 | Normal |\n| Glucose | 92 mg/dL | 70\u201399 | Normal |\n| BUN | 16 mg/dL | 7\u201320 | Normal |\n| Creatinine | 0.8 mg/dL | 0.6\u20131.2 | Normal |\n| AST | 22 U/L | 10\u201340 | Normal |\n| ALT | 24 U/L | 10\u201340 | Normal |\n\n#### **4.3 LIPID PANEL**\n\n| Parameter | Value | Reference Range | Interpretation |\n|----------|-------|------------------|----------------|\n| Total Cholesterol | 185 mg/dL | <200 | Normal |\n| LDL-C | 95 mg/dL | <100 | Normal |\n| HDL-C | 52 mg/dL | >40 | Normal |\n| Triglycerides | 110 mg/dL | <150 | Normal |\n\n#### **4.4 THYROID FUNCTION TEST (TFT)**\n\n| Parameter | Value | Reference Range | Interpretation |\n|----------|-------|------------------|----------------|\n| TSH | 2.1 \u00b5IU/mL | 0.4\u20134.0 | Normal |\n| Free T4 | 1.1 ng/dL | 0.8\u20131.8 | Normal |\n| Free T3 | 2.6 pg/mL | 2.0\u20134.4 | Normal |"
        },
        {
            id: 'clinical-note',
            label: 'Clinical Note',
            badge: 'Specialty',
            badgeClass: 'specialty',
            content: "**Clinical Note**\n\n**Patient Name:** Johnathon \"Jon\" Elwood  \n**Medical Record Number (MRN):** 100456789  \n**Date of Service:** 03/18/2025  \n**Time of Service:** 09:45 AM  \n**Attending Physician:** Dr. Elena M. Torres, MD  \n**Specialty:** Internal Medicine  \n**Facility:** Evergreen Regional Medical Center  \n**Type of Note:** Progress Note  \n**Chief Complaint:** Fever, chills, productive cough, and generalized weakness for 5 days.  \n**Reason for Admission:** Suspected community-acquired pneumonia with worsening symptoms over the past 5 days.\n\n---\n\n**Subjective Data:**\n\nThe patient, a 42-year-old male, presents with a 5-day history of fever, chills, productive cough, and generalized weakness. He reports a temperature of up to 102.4\u00b0F (39.1\u00b0C) with chills occurring 2\u20133 times daily. The cough is productive, with yellow-green sputum. He states he has been feeling increasingly fatigued and has not been able to perform his usual activities of daily living. He also notes a recent 20-pound weight loss over the past 2 months.\n\n---\n\n**Objective Data:**\n\n**Vital Signs:**\n- Blood Pressure: 142/88 mmHg\n- Heart Rate: 102 bpm\n- Respiratory Rate: 20 breaths/min\n- Oxygen Saturation (on room air): 94%\n- Temperature: 102.4\u00b0F (39.1\u00b0C)\n- Weight: 198 lbs (90 kg)\n- BMI: 28.3 (overweight)\n\n**Respiratory:** Clear to auscultation bilaterally. Mild crackles noted at the right lower lung field.\n\n**Laboratory Results:**\n\n- **CBC:**\n  - Hemoglobin: 13.2 g/dL\n  - WBC: 15.6 x 10^9/L\n  - Neutrophils: 11.8 x 10^9/L (75.6%)\n  - Platelets: 220 x 10^9/L\n\n- **Blood Chemistry:**\n  - Sodium: 140 mEq/L\n  - Potassium: 4.2 mEq/L\n  - Glucose: 108 mg/dL\n  - BUN: 24 mg/dL\n  - Creatinine: 1.1 mg/dL\n  - AST: 38 U/L\n  - ALT: 42 U/L\n\n- **CRP:** 95 mg/L\n- **ESR:** 42 mm/hr\n\n**Chest X-ray:** Increased density in the right lower lobe with evidence of consolidation.\n\n---\n\n**Assessment and Plan:**\n\n**Primary Diagnosis:**\n- **Community-Acquired Pneumonia (CAP)**: Based on clinical presentation, elevated WBC, CRP, and chest X-ray findings.\n\n**Plan:**\n- Start levofloxacin 500 mg PO daily\n- Start ceftriaxone 1 g IV every 24 hours\n- Oxygen therapy via nasal cannula at 2 L/min\n- Acetaminophen 650 mg PO every 6 hours PRN for fever\n- Repeat chest X-ray in 72 hours  "
        }
    ];

    /* --- Simple markdown-to-HTML renderer --- */
    function renderMarkdown(text) {
        var lines = text.split('\n');
        var html = [];
        var inList = false;

        for (var i = 0; i < lines.length; i++) {
            var line = lines[i];

            // Horizontal rules
            if (/^---+\s*$/.test(line)) {
                if (inList) { html.push('</ul>'); inList = false; }
                html.push('<hr>');
                continue;
            }

            // Headers (### **...**)
            if (/^###\s+/.test(line)) {
                if (inList) { html.push('</ul>'); inList = false; }
                var headerText = line.replace(/^###\s+/, '').replace(/\*\*/g, '');
                html.push('<h3>' + escapeHtml(headerText) + '</h3>');
                continue;
            }

            // List items
            if (/^\s*-\s+/.test(line)) {
                if (!inList) { html.push('<ul>'); inList = true; }
                var itemText = line.replace(/^\s*-\s+/, '');
                html.push('<li>' + formatInline(itemText) + '</li>');
                continue;
            }

            // Close list if we hit a non-list line
            if (inList) { html.push('</ul>'); inList = false; }

            // Empty lines
            if (line.trim() === '') {
                html.push('<br>');
                continue;
            }

            // Regular lines
            html.push('<p>' + formatInline(line) + '</p>');
        }

        if (inList) { html.push('</ul>'); }
        return html.join('\n');
    }

    function escapeHtml(str) {
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function formatInline(text) {
        // Escape HTML first
        text = escapeHtml(text);

        // Bold: **...**
        text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // Color-code vital signs (BP, HR, Temp, SpO2, RR patterns)
        text = text.replace(/(\d+\/\d+\s*mmHg)/g, '<span class="vital">$1</span>');
        text = text.replace(/(\d+\s*bpm)/g, '<span class="vital">$1</span>');
        text = text.replace(/(\d+\.?\d*\s*°F)/g, '<span class="vital">$1</span>');
        text = text.replace(/(SpO[₂2]:\s*\d+%)/g, '<span class="vital">$1</span>');
        text = text.replace(/(\d+%\s*on room air)/g, '<span class="vital">$1</span>');
        text = text.replace(/(\d+\s*breaths\/min)/g, '<span class="vital">$1</span>');

        // Color-code lab values (g/dL, mg/dL, mEq/L, etc.)
        text = text.replace(/(\d+\.?\d*\s*(?:g\/dL|mg\/dL|mEq\/L|mmol\/L|U\/L|ng\/mL|µIU\/mL|ng\/dL|pg\/mL|mm\/hr|mg\/L))/g, '<span class="lab-value">$1</span>');

        // Color-code medications (common patterns like "mg daily", "mg BID", "mg PO")
        text = text.replace(/((?:lisinopril|atorvastatin|metformin|omeprazole|levothyroxine|topiramate|amlodipine|metoprolol|aspirin|warfarin|simvastatin|furosemide|sertraline|ceftriaxone|levofloxacin|acetaminophen|ibuprofen|hydromorphone|ondansetron|metoclopramide|digoxin|celecoxib|duloxetine|clopidogrel|albuterol|fluticasone|insulin glargine|ciprofloxacin|tamsulosin|glimepiride)\s+\d+[^,<)]*)/gi, '<span class="medication">$1</span>');

        return text;
    }

    /* --- Initialize document preview tabs --- */
    var tabsContainer = document.getElementById('doc-tabs');
    var previewContainer = document.getElementById('doc-preview');

    if (tabsContainer && previewContainer) {
        // Build tabs
        docPreviews.forEach(function (doc, index) {
            var tab = document.createElement('button');
            tab.className = 'doc-tab' + (index === 0 ? ' active' : '');
            tab.innerHTML = '<span class="tab-badge ' + doc.badgeClass + '">' + doc.badge + '</span> ' + doc.label;
            tab.setAttribute('data-index', index);
            tab.addEventListener('click', function () {
                selectDoc(index);
            });
            tabsContainer.appendChild(tab);
        });

        // Select a document
        function selectDoc(index) {
            var tabs = tabsContainer.querySelectorAll('.doc-tab');
            tabs.forEach(function (t) { t.classList.remove('active'); });
            tabs[index].classList.add('active');
            previewContainer.innerHTML = renderMarkdown(docPreviews[index].content);
            previewContainer.scrollTop = 0;
        }

        // Show first document by default
        selectDoc(0);
    }
})();
