################################################################################
#   File Name: ExperimentViews.py
#
#   File Author: Rohit Singh
#
#   File Description:
#     This file routes our experiment views
#     to the backend
#
#   File History:
#   2020-11-05: ExperimentViews.py created from old views.py
#   2020-11-02: (views.py) Created by Rohit
#
###############################################################################
# Imports ----------------------------------------------------------------------
# Django Libraries
from django.shortcuts import render, redirect
from django.utils import timezone
from django.conf import settings
from django.http import HttpResponse, Http404
# Local Imports
from ..models import TestConfiguration, Experiment, Result
# Python Libraries
import os
import csv
import numpy as np
from matplotlib import pyplot as plt
from pathlib import Path
from email.message import EmailMessage
from dotenv import load_dotenv
import smtplib
# ..... Experiments ............................................................
################################################################################
#   Function Name: Experiments
#   Function Author: Rohit
#   Function Description: Renders the Experiments page
#   Inputs: request | Outputs: Experiments.html {ctx}
################################################################################
def Experiments(request):
    l_Experiments = Experiment.objects.all()
    l_TestConfigurations = TestConfiguration.objects.all()
    context = {
        'l_Experiments': l_Experiments,
        'l_TestConfigurations': l_TestConfigurations,
        's_Error': "None",
        'b_Saved': False
    }
    return render(request, 'DataCollection/Experiments.html', context)
################################################################################
#   Function Name: CreateNewExperiment
#   Function Author: Rohit
#   Function Description: Creates new Experiment and loads
#                           Experiments page again
#   Inputs: request | Outputs: experiments.html {ctx}
################################################################################
def CreateNewExperiment(request):
    # Create our new base Experiment object
    exp = Experiment()
    # The form data is accessed by request.POST.get()
    try:
        b_ResultExistsAlready = True
        m_result = Result.objects.get(s_FileName="SampleTest.csv")
    except Exception as e:
        b_ResultExistsAlready = False
    if not b_ResultExistsAlready:
        m_Result = Result(s_FileName="SampleTest.csv")
        m_Result.save()
    # save created object
    try:
        exp.s_ExperimentName    = request.POST.get('s_ExperimentName')
        exp.i_ExperimentId      = int(request.POST.get('i_ExperimentId'))
        exp.d_Date              = timezone.now()
        testConfigId = request.POST.get('m_TestConfiguration')
        exp.m_TestConfiguration= TestConfiguration.objects.get(pk=testConfigId)
        exp.s_ResultsFile = request.POST.get('s_ResultsFile')
        exp.s_EmailAddress = request.POST.get('s_EmailAddress')
        # Check if we need to create a new results object

        exp.save()
        # If we haven't encountered an error, exp is saved
        s_Error = "None"
        b_Saved = True

    except Exception as e:
        s_Error = str(e)
        if s_Error == "invalid literal for int() with base 10: ''":
            s_Error = "Please enter a value for all fields"
        b_Saved = False

    # Generate some context
    l_Experiments = Experiment.objects.all()
    l_TestConfigurations = TestConfiguration.objects.all()
    context = {
        'l_Experiments': l_Experiments,
        'l_TestConfigurations': l_TestConfigurations,
        's_Error': s_Error,
        'b_Saved': b_Saved
    }
    return render(request, 'DataCollection/Experiments.html', context)

################################################################################
#   Function Name: ExperimentDetail
#   Function Author: Rohit
#   Function Description: Renders ExperimentDetail.html
#   Inputs: request | Outputs: ExperimentDetail.html {ctx}
################################################################################
def ExperimentDetail(request, i_ExperimentId):
    # First, get the results of the experiment we are looking at
    m_Experiment = Experiment.objects.get(i_ExperimentId = i_ExperimentId)
    m_TestConfiguration = m_Experiment.m_TestConfiguration
    m_Result = Result.objects.get(s_FileName = m_Experiment.s_ResultsFile)

    # Next, send the results file to the javascript to be handled
    M_data  = m_Result.LoadResultsAsMatrix()
    i_NumCols = np.shape(M_data)[1]

    # Due to memory constraints, only define 5 columns to send
    columnIndices   = [1,2,7,8,9]
    labels          = []
    datas           = []
    for idx in columnIndices:
        m_Result.i_ColumnIdx = idx
        labels.append(m_Result.GetColumnByIndex()[0])
        datas.append(m_Result.GetColumnByIndex().tolist()[2:])

    ctx = {
        'experiment': m_Experiment,
        'tc': m_TestConfiguration,
        'data': datas,
        'labels': labels
    }

    return render(request, 'DataCollection/ExperimentDetail.html', ctx)

################################################################################
#   Function Name: DownloadResults
#   Function Author: Rohit
#   Function Description: Downloads .csv file
#   Inputs: request | Outputs: .csv file
################################################################################
def DownloadResults(request, s_ResultsFile):
    print(s_ResultsFile)
    m_Result        = Result.objects.get(s_FileName=s_ResultsFile)
    s_csvFilePath   = m_Result.LoadResultsFilepath()
    if s_csvFilePath == -1:
        raise Http404
    else:
        with open(s_csvFilePath, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(s_csvFilePath)
            return response

###############################################################################
#   Function Name: GeneratePlot
#   Function Author: Rohit
#   Function Description:   Creates plot from csv data
#                           Saves plot in TestResults
#                           Downloads plot from window
#
#   Inputs: request, s_ResultsFile | Outputs: plot.png
#
#   History:
#       2020-11-03: Sliding Window Measurements added
#       2020-11-02: Created by Rohit
################################################################################
# TODO: If the path doesn't exist, give the user an error
# TODO: Add more error case handling
def GeneratePlot(request, s_ResultsFile):
    # Load results object
    m_Result = Result.objects.get(s_FileName=s_ResultsFile)
    # load results as matrix
    M_data = m_Result.LoadResultsAsMatrix()
    # Retrieve Data from the form
    s_XValuesLabel  = request.POST.get('s_XValuesLabel')
    s_YValuesLabel  = request.POST.get('s_YValuesLabel')
    i_StartTime     = request.POST.get('i_StartTime')
    i_EndTime       = request.POST.get('i_EndTime')
    # TODO: Fix this logic
    b_spliceData = not (i_StartTime == i_EndTime)
    if b_spliceData:
        i_StartTimeIdx  = -1
        i_EndTimeIdx    = -1
    # Create blank arrays for the data to be plotted
    a_XValues = []
    a_YValues = []
    # Fill the arrays by iterating over the rows
    for i in range(1, len(M_data)):
        a_XValues.append(float(M_data[i, int(s_XValuesLabel)]))
        a_YValues.append(float(M_data[i, int(s_YValuesLabel)]))
        # If user wants to splice their data, find the bounds
        if b_spliceData:
            # Find index for start / end times
            if float(M_data[i, 1]) > float(i_StartTime) and i_StartTimeIdx == -1:
                i_StartTimeIdx = i
            if float(M_data[i, 1]) > float(i_EndTime) and i_EndTimeIdx == -1:
                i_EndTimeIdx = i
    # Clear any previously saved plot info
    plt.cla()
    # If the user doesn't want their data spliced, don't!
    if b_spliceData == False:
        plt.plot(a_XValues, a_YValues)
    # Else if the user does want their data spliced, do it!
    else:
        plt.plot(a_XValues[i_StartTimeIdx:i_EndTimeIdx], a_YValues[i_StartTimeIdx:i_EndTimeIdx])
    # Decorate our plot
    plt.title(f"{M_data[0, int(s_YValuesLabel)]} as a function of {M_data[0, int(s_XValuesLabel)]}")
    plt.xlabel(f"{M_data[0, int(s_XValuesLabel)]}")
    plt.ylabel(f"{M_data[0, int(s_YValuesLabel)]}")
    plt.grid()
    # Save the plot to figures directory and download it from there
    s_FilePath = './DataCollection/TestResults/Figures/Save.png'
    filePath = os.path.join(settings.MEDIA_ROOT, s_FilePath)
    plt.savefig(filePath)
    if os.path.exists(filePath):
        with open(filePath, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(filePath)
            return response
    # TODO: Error handling here
    return redirect('/DataCollection/Experiments')
###############################################################################
#   Function Name: SendEmail
#   Function Author: Rohit
#   Function Description:   Sends all test info to email
#
#   Inputs: Experiment | Output: Email
#
#   History:
#       2020-11-05: Created by Rohit
################################################################################
# TODO: Fix this Function
def sendEmail(experiment):
    # Get secrets
    load_dotenv('./DataCollection/.env')
    s_EmailAddress  = os.getenv("EMAILADDRESS")
    s_EmailPassword = os.getenv("EMAILPASSWORD")
    # Create Email message
    msg = EmailMessage()
    msg['Subject']  = f'FTU Test Results: {experiment.s_ExperimentName}'
    msg['From']     = s_EmailAddress
    msg['To']       = experiment.s_EmailAddress
    s_FilePath = './DataCollection/TestResults/' + experiment.s_ResultsFile
    filePath = os.path.join(settings.MEDIA_ROOT, s_FilePath)
    # Verify the files existence
    if os.path.exists(filePath):
        with open(filePath, 'rb') as fh:
            file = fh.read()
        #msg.add_attachment(file, maintype='doc', subtype='csv', filename=f"FTUTestResults")
    # Create Email Body
    a_EmailBodyArray = []
    a_EmailBodyArray.append(f"{experiment.s_ExperimentName} was created at {experiment.d_Date}\n")
    a_EmailBodyArray.append(f"Test was using test configuration '{experiment.m_TestConfiguration.s_TestDesc}'")
    a_EmailBodyArray.append(f"Desired Temperature: {experiment.m_TestConfiguration.i_DesiredTemp} Centigrade")
    a_EmailBodyArray.append(f"Desired Voltage: {experiment.m_TestConfiguration.i_DesiredVoltage} Volts")
    a_EmailBodyArray.append(f"Desired Test Time: {experiment.m_TestConfiguration.i_DesiredTestTime} Seconds")
    a_EmailBodyArray.append(f"Desired Magnetic Field: {experiment.m_TestConfiguration.i_DesiredField} Milli-Teslas")
    a_EmailBodyArray.append(f"Desired Serial Rate: {experiment.m_TestConfiguration.i_DesiredSerialRate}")
    s_EmailBody = "\n".join(a_EmailBodyArray)
    # Attach email body
    msg.set_content(s_EmailBody)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(user=s_EmailAddress, password=s_EmailPassword)
        smtp.send_message(msg)

###############################################################################
#   Function Name: GenerateLineGraph
#   Function Author: Rohit
#   Function Description:   Creates line graph
#
#   Inputs: Request | Output: graph
#
#   History:
#       2020-11-10: Created by Rohit
################################################################################
def GenerateLineGraph(request, i_ExperimentId):
    # First, get the results of the experiment we are looking at
    m_Experiment = Experiment.objects.get(i_ExperimentId = i_ExperimentId)
    m_TestConfiguration = m_Experiment.m_TestConfiguration
    m_Result = Result.objects.get(s_FileName = m_Experiment.s_ResultsFile)

    # Next, send the results file to the javascript to be handled
    M_data  = m_Result.LoadResultsAsMatrix()
    i_NumCols = np.shape(M_data)[1]

    # Due to memory constraints, only define 5 columns to send
    columnIndices   = [1,2,7,8,9]
    labels          = []
    datas           = []
    # Go through the columns and sort them accordingly
    for idx in columnIndices:
        m_Result.i_ColumnIdx = idx
        # The first element of a column contains it's label
        labels.append(m_Result.GetColumnByIndex()[0])
        # The remaining elements of a column contain its data
        datas.append(m_Result.GetColumnByIndex().tolist()[2:])

    # Generate some ctx
    ctx = {
        'experiment': m_Experiment,
        'tc': m_TestConfiguration,
        'data': datas,
        'labels': labels
    }

    return render(request, 'DataCollection/ExperimentDetail.html', ctx)
