import pandas as pd
import numpy as np
from scipy import stats
from progress.bar import Bar
from sklearn.preprocessing import LabelEncoder

from utils import log, convertFullDate


def checkForDuplicates(accounts, cards, clients, dispositions, districts, loans, transactions, verbose):
    """Checks for duplicates in all the tables

    Args:
        accounts (DataFrame): accounts table
        cards (DataFrame): cards table
        clients (DataFrame): clients table
        dispositions (DataFrame): dispositions table
        districts (DataFrame): districts table
        loans (DataFrame): loans table
        transactions (DataFrame): transactions table
        verbose (bool): controls console logs
    """
    accounts_duplicates = accounts[accounts.duplicated('account_id')].shape[0]
    cards_duplicates = cards[cards.duplicated('card_id')].shape[0]
    clients_duplicates = clients[clients.duplicated('client_id')].shape[0]
    dispositions_duplicates = dispositions[dispositions.duplicated('disp_id')].shape[0]
    districts_duplicates = districts[districts.duplicated('code ')].shape[0]
    loans_duplicates = loans[loans.duplicated('loan_id')].shape[0]
    transactions_duplicates = transactions[transactions.duplicated('trans_id')].shape[0]

    logMessage = "Dataset Duplicates:\nAccounts: "+ str(accounts_duplicates) + "\nCards: " + str(cards_duplicates) + "\nClients: " + str(clients_duplicates) + "\nDispositions: " + str(dispositions_duplicates) + "\nDistricts: " + str(districts_duplicates) + "\nLoans: " + str(loans_duplicates) + "\nTransactions: " + str(transactions_duplicates) + "\n"
    log(logMessage, verbose)
    return


def printDatasetSizes(accounts, cards, clients, dispositions, districts, loans, transactions, verbose):
    """Prints the tables' sizes

    Args:
        accounts (DataFrame): accounts table
        cards (DataFrame): cards table
        clients (DataFrame): clients table
        dispositions (DataFrame): dispositions table
        districts (DataFrame): districts table
        loans (DataFrame): loans table
        transactions (DataFrame): transactions table
        verbose (bool): controls console logs
    """
    accounts_size = accounts.shape[0]
    cards_size = cards.shape[0]
    clients_size = clients.shape[0]
    dispositions_size = dispositions.shape[0]
    districts_size = districts.shape[0]
    loans_size = loans.shape[0]
    transactions_size = transactions.shape[0]

    logMessage = "Dataset Sizes:\nAccounts: "+ str(accounts_size) + "\nCards: " + str(cards_size) + "\nClients: " + str(clients_size) + "\nDispositions: " + str(dispositions_size) + "\nDistricts: " + str(districts_size) + "\nLoans: " + str(loans_size) + "\nTransactions: " + str(transactions_size) + "\n"
    log(logMessage, verbose)
    return


def combineFeatures(loans, clients, dispositions, genders, ageGroups, effortRates, savingsRates, districtCrimeRates, expenses, ages):
    """Process all data to correspond to a loan row, in order to combine all data with loans table

    Args:
        loans (DataFrame): loans table
        clients (DataFrame): clients table
        dispositions (DataFrame): dispositions table
        genders (array): sorted genders array
        ageGroups (array): sorted age groups array
        effortRates (dict): accounts' effort rates
        savingsRates (dict): accounts' savings rates
        districtCrimeRates (dict): crime rate per district
        expenses (dict): expenses per account
        ages (array): sorted ages

    Returns:
        DataFrame: processed data with all the created features
    """
    progressBar = Bar('Features Processing', max=loans.shape[0], suffix='%(percent)d%% - %(eta)ds               ')
    gendersByLoan = []
    ageGroupByLoan = []
    effortRateByLoan = []
    savingsRateByLoan = []
    distCrimeByLoan = []
    expensesByLoan =  []
    agesByLoan = []

    for _, row in loans.iterrows():
        accountId = row['account_id']
        loanId = row['loan_id']
        clientId = None

        # treating genders and ageGroups
        for _, rowDisp in dispositions.iterrows():
            if rowDisp['account_id'] == accountId:
                clientId = rowDisp['client_id']

        if clientId != None:
            indexes = clients.index
            indexesBool = clients['client_id'] == clientId
            clientIndex = indexes[indexesBool][0]

            gendersByLoan.append(genders[clientIndex])
            ageGroupByLoan.append(ageGroups[clientIndex])
            agesByLoan.append(ages[clientIndex])
        else:
            print('ClientId None')

        # treating the rest of the features
        effortRateByLoan.append(effortRates[loanId])
        savingsRateByLoan.append(savingsRates[loanId])
        distCrimeByLoan.append(districtCrimeRates[accountId])
        try:
            expensesByLoan.append(expenses[accountId])
        except KeyError:
            expensesByLoan.append(0)
        progressBar.next()
    return (gendersByLoan, ageGroupByLoan, effortRateByLoan, savingsRateByLoan, distCrimeByLoan, expensesByLoan, agesByLoan)


def cleanData(loansDataFrame):
    """Removes redundant attributes

    Args:
        loansDataFrame (DataFrame): loans data

    Returns:
        DataFrame: clean data
    """
    print('\nRemoving Redundant Information...')
    columnsToRemove =  ['loan_id', 'account_id']
    noRedundantData = loansDataFrame

    for col in columnsToRemove:
        noRedundantData = noRedundantData.drop(col, axis=1)
    return noRedundantData


def removeOutliers(loansDataFrame):
    """Removes the outliers based on the z-score

    Args:
        loansDataFrame (DataFrame): loans data

    Returns:
        DataFrame: data without outliers
    """
    print('Removing Outliers...\n')
    nonCategoricalColumns = ['savingsRate', 'distCrime', 'amount', 'duration', 'payments', 'expenses']
    totalOutliers = 0
    result = loansDataFrame

    for col in nonCategoricalColumns:
        prevSize = result.shape[0]
        result = result[(np.abs(stats.zscore(result[col])) < 3)]
        size = result.shape[0]
        print('Column  ', col, ' had ', prevSize-size, ' outliers')
        totalOutliers += prevSize-size

    print('Removed a total of  ', totalOutliers, ' outliers')
    return result


def labelEncoding(loansDataFrame):
    """Encodes the features to maintain algorithms compatibility

    Args:
        loansDataFrame (DataFrame): loans data

    Returns:
        DataFrame: encoded data
    """
    print('Encoding data...')

    # gender and ageGroup encoding
    le = LabelEncoder()

    encodedGender = le.fit_transform(loansDataFrame['gender'])
    encodedAgeGroup = le.fit_transform(loansDataFrame['ageGroup'])

    encodedDataFrame = loansDataFrame.drop("gender", axis=1)
    encodedDataFrame = encodedDataFrame.drop("ageGroup", axis=1)

    encodedDataFrame["gender"] = encodedGender
    encodedDataFrame["ageGroup"] = encodedAgeGroup

    # splitting date into year, month, day
    years = []
    months = []
    days = []

    for _, row in encodedDataFrame.iterrows():
        date = convertFullDate(str(row['date']))

        years.append(date.year)
        months.append(date.month)
        days.append(date.day)

    encodedDataFrame = encodedDataFrame.drop("date", axis=1)

    # encodedDataFrame['year'] = years # Year doesn't make sense, because the model is going to be used in future years
    encodedDataFrame['month'] = months
    encodedDataFrame['day'] = days
    return encodedDataFrame


def processZeroSalaries(salaries, districtAvgSalary, substituteWithAvg):
    """Process zero salaries, replacing them with the district average

    Args:
        salaries (dict): salaries by account id
        districtAvgSalary (dict): average salary by account id
        substituteWithAvg (bool): controls wether the replacement takes place

    Returns:
        dict: salaries by account id
    """
    processedSalaries = {}
    nSalaries = len(salaries)
    nZeroSalaries = 0

    for accountId in salaries:
        if salaries[accountId] == 0:
            nZeroSalaries+=1
            if substituteWithAvg:
                processedSalaries[accountId] = districtAvgSalary[accountId]
            else:
                processedSalaries[accountId] = 1
        else:
            processedSalaries[accountId] = salaries[accountId]

    print("\nNumber of zero salaries: ", nZeroSalaries, " of a total of ", nSalaries)
    return processedSalaries
