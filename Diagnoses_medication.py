# This code is adapted from MED2VEC paper and modified to add medications, time gap information
# In[]:
import _pickle as pickle
from datetime import datetime
from datetime import date
import pandas as pd
print("import successful")

# In[]:
def convert_to_icd9(dxStr):
    if dxStr.startswith('E'):
        if len(dxStr) > 4:
            return dxStr[:4] + '.' + dxStr[4:]
        else:
            return dxStr
    else:
        if len(dxStr) > 3:
            return dxStr[:3] + '.' + dxStr[3:]
        else:
            return dxStr


def convert_to_3digit_icd9(dxStr):
    if dxStr.startswith('E'):
        if len(dxStr) > 4:
            return dxStr[:4]
        else:
            return dxStr
    else:
        if len(dxStr) > 3:
            return dxStr[:3]
        else:
            return dxStr


# In[]:
admissionFile = 'ADMISSIONS.csv'
diagnosisFile = 'DIAGNOSES_ICD.csv'
prescriptionsFile = 'PRESCRIPTIONS.csv'
outFile = 'readmission_final2'

# In[]:
print('Building pid-admission mapping, admission-date mapping')
pidAdmMap = {}
admDateMap = {}
disDateMap = {}
infd = open(admissionFile, 'r')
infd.readline()
for line in infd:
    tokens = line.strip().split(',')
    pid = int(tokens[1])
    admId = int(tokens[2])
    admTime = datetime.strptime(tokens[3], '%Y-%m-%d %H:%M:%S')
    disTime = datetime.strptime(tokens[4], '%Y-%m-%d %H:%M:%S')
    
    admDateMap[admId] = admTime
    disDateMap[admId] = disTime
    if pid in pidAdmMap:
        pidAdmMap[pid].append(admId)
    else:
        pidAdmMap[pid] = [admId]
infd.close()

# In[]:
print('Building admission-dxList mapping')
admDxMap = {}  
admDxMap_3digit = {}  
infd = open(diagnosisFile, 'r')
infd.readline()
for line in infd:
    tokens = line.strip().split(',')
    admId = int(tokens[2])
    dxStr = 'D_' + convert_to_icd9(tokens[4][1:-1])  # Uncomment this line and comment the line below,
                                            #  if you want to use the entire ICD9 digits.
    dxStr_3digit = 'D_' + convert_to_3digit_icd9(tokens[4][1:-1])

    if admId in admDxMap:
        admDxMap[admId].append(dxStr)
    else:
        admDxMap[admId] = [dxStr]

    if admId in admDxMap_3digit:
        admDxMap_3digit[admId].append(dxStr_3digit)
    else:
        admDxMap_3digit[admId] = [dxStr_3digit]

infd.close()

# In[]:

print('Building medications mapping')
admNDCMap = {}
prescriptions = pd.read_csv(prescriptionsFile)
prescriptions_ = prescriptions.dropna(subset=['NDC'])
medications_ndc = list(prescriptions_.values.tolist())
count = 0
for line in medications_ndc:
   admId = line[2]
   code = int(line[12])
   
   if int(code) != 0:
        code = str(code)[4:8]
        code = int(float(code))
   try:
       if admId in admNDCMap:
           admNDCMap[admId].append(code)
       else:
           admNDCMap[admId] = [code]
   except ValueError:
       pass


# In[]:
print('Building pid-sortedVisits mapping')
pidSeqMap = {}  
pidSeqMap_3digit = {}  
for pid, admIdList in pidAdmMap.items():
    if len(admIdList) < 2: continue
    sortedList = sorted([(admDateMap[admId], admDxMap[admId], disDateMap[admId], admNDCMap[admId], admId)
                         if admId in admNDCMap
                         else (admDateMap[admId], admDxMap[admId], disDateMap[admId], [0], admId) for admId in admIdList])
    pidSeqMap[pid] = sortedList
    sortedList_3digit = sorted([(admDateMap[admId], admDxMap_3digit[admId], disDateMap[admId], admNDCMap[admId], admId)
                        if admId in admNDCMap
                        else (admDateMap[admId], admDxMap_3digit[admId], disDateMap[admId], [0], admId) for admId in admIdList])
    pidSeqMap_3digit[pid] = sortedList_3digit
print(len(pidSeqMap), len(pidSeqMap_3digit))


# In[]:
print('Building pids, dates, strSeqs')
pids = []
dates = []
seqs = []
med_codes = []
adm_ids = []
for pid, visits in pidSeqMap.items():
    pids.append(pid)
    seq = []
    date = []
    medication = []
    adm_id = []
    for visit in visits:
        date.append(visit[0])
        seq.append(visit[1])
        medication.append(visit[3])
        adm_id.append(visit[4])
    dates.append(date)
    seqs.append(seq)
    med_codes.append(medication)
    adm_ids.append(adm_id)

# In[]:
print('Building pids, dates, strSeqs for 3digit ICD9 code')
seqs_3digit = []
total_visit_duration = []
los = []
ending_list = [-1]
for pid, visits in pidSeqMap_3digit.items():
    idx = 1
    seq = []
    time = []  # added
    dis_time = []
    duration = []  # added
    los_visit = []
    for visit in visits:
        time.append(visit[0])  # added has one patient adm time for all admissions
        seq.append(visit[1])
        dis_time.append(visit[2])
    seqs_3digit.append(seq)
    previous_time = time[0].date()
    # below for loop included to add the duration between two visits in days
    for adtime, distime in (zip(time, dis_time)):
        los_visit = [(distime.date() - adtime.date()).days]
        los.append(los_visit)
    los.extend([ending_list])
    for time_, dis in (zip(time, dis_time)):
        duration = [(time_.date() - previous_time).days]
        if duration[0] < 0:
            duration = [0]
        previous_time = dis.date()
        total_visit_duration.append(duration)
    total_visit_duration.extend([ending_list])
total_visit_duration = total_visit_duration[:-1]
los = los[:-1]

# In[]:
print('Converting strSeqs to intSeqs, and making types')
types = {}
newSeqs = []
for patient in seqs:
    newPatient = []
    for visit in patient:
        newVisit = []
        for code in visit:
            if code in types:
                newVisit.append(types[code])
            else:
                types[code] = len(types)
                newVisit.append(types[code])
        newPatient.append(newVisit)
    newSeqs.append(newPatient)


# In[]:
print('Converting strSeqs to intSeqs, and making types for 3digit ICD9 code')
types_3digit = {}
newSeqs_3digit = []

i = 0
for patient in seqs_3digit:
    newPatient = []
    visit_dur = []  # added
    temp_visit = len(total_visit_duration[i])
    j = 0
    for visit in patient:
        newVisit = []
        for code in set(visit):
            if code in types_3digit:
                newVisit.append(types_3digit[code])
            else:
                types_3digit[code] = len(types_3digit)
                newVisit.append(types_3digit[code])
        j = j + 1
        newPatient.append(newVisit)

    i = i + 1
    newSeqs_3digit.append(newPatient)

# In[]:
print('Re-formatting to Med2Vec dataset')
seqs = []
drug_codes = []
hadm_ids = []
for adm in adm_ids:
    hadm_ids.extend(adm)
    hadm_ids.append([-1])
hadm_ids = hadm_ids[:-1]
for patient in newSeqs:
    seqs.extend(patient)
    seqs.append([-1])
seqs = seqs[:-1]

for codes in med_codes:
   drug_codes.extend(codes)
   drug_codes.append([-1])
drug_codes = drug_codes[:-1]

seqs_3digit = []
for patient in newSeqs_3digit:
    seqs_3digit.extend(patient)
    seqs_3digit.append([-1])
seqs_3digit = seqs_3digit[:-1]

print(len(hadm_ids), len(seqs), len(total_visit_duration), len(drug_codes), len(los))

# In[]:

pickle.dump(drug_codes, open(outFile + '.medication', 'wb'), -1)
pickle.dump(seqs, open(outFile + '.seqs', 'wb'), -1)
pickle.dump(types, open(outFile + '.types', 'wb'), -1)
pickle.dump(seqs_3digit, open(outFile + '.3digitICD9.seqs', 'wb'), -1)
pickle.dump(types_3digit, open(outFile + '.3digitICD9.types', 'wb'), -1)
pickle.dump(total_visit_duration, open(outFile + '.time', 'wb'), -1)
pickle.dump(los, open(outFile + '.los', 'wb'), -1)
