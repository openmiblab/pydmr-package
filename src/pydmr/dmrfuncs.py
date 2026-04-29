import os
import pydmr.rw
import pydmr.pydict


def pars_to_wide(dmr_file, wide_file):
    """Save parameter values in wide-format csv shape

    Args:
        dmr_file (dmr file name): Source file
        wide_file (csv file name): Output file
    """
    table_long = pydmr.read(dmr_file, format='pandas')['pars']
    table_wide = table_long.pivot(index=['subject', 'study'], columns='parameter', values='value')
    table_wide.to_csv(wide_file)


def pars_to_long(dmr_file, long_file):
    """Save parameter values in long-format csv shape

    Args:
        dmr_file (dmr file name): Source file
        long_file (csv file name): Output file
    """
    dmr = pydmr.read(dmr_file, format='pandas')
    table_long = dmr['pars']
    parameters = table_long.parameter.values.tolist()
    extra_columns = metadata(dmr_file, parameters)
    cols = ['description', 'unit', 'type']
    if 'columns' in dmr:
        cols += dmr['columns']
    for c, col in enumerate(cols):
        table_long[col] = [extra_columns[p][c] for p in range(len(parameters))]
    table_long.to_csv(long_file, index=False)


def metadata(file, parameters, attribute=None):
    """Return given metadata for a list of parameters

    Args:
        file (str): dmr file
        parameters (str or list): parameter or list of parameters for 
            which the attribute is requested.
        attribute (str or list): attribute(s) in the metadata to return. 
            If this is None, all metadata are returned.

    Returns:
        str or list: metadata values for all parameters in the list
    """
    dmr = pydmr.rw.read(file)
    cols = ['description', 'unit', 'type']
    if 'columns' in dmr:
        cols += dmr['columns']
    if attribute is None:
        attribute = cols
    ind = {item: index for index, item in enumerate(cols)}
    if isinstance(attribute, str):
        if isinstance(parameters, str):
            return dmr['data'][parameters][ind[attribute]]
        else:
            return [dmr['data'][p][ind[attribute]] for p in parameters]
    else:
        if isinstance(parameters, str):
            return [dmr['data'][parameters][ind[a]] for a in attribute]
        else:
            return [
                [dmr['data'][p][ind[a]] for a in attribute]
                for p in parameters
            ]       


def drop(file, result=None, subject=None, study=None, parameter=None, **kwargs):
    """Drop subjects, studies or parameters from the dataset

    Args:
        file (str): dmr file.
        result (str, optional): Filename to save result. If this is 
            not provided, the input file is overwritten. Defaults to None.
        subject (str or list, optional): subject or list of subjects 
            to drop. Defaults to None.
        study (str or list, optional): subject or list of subjects 
            to drop. Defaults to None.
        parameter (str or list, optional): parameter or list of 
            parameters to drop. Defaults to None.
        kwargs (dict): drop parameters based on attributes in the 
            data dictionary.
    Returns:
        str : the resulting file
    """

    data = pydmr.rw.read(file)
    data = pydmr.pydict.dict_drop(data, subject, study, parameter, **kwargs)
    if result is None:
        pydmr.rw.write(file, data)
        return file
    else:
        pydmr.rw.write(result, data)
        return result


def keep(file, result=None, subject=None, study=None, parameter=None, **kwargs):
    """Select specific subjects, studies or parameters from the dataset

    Args:
        file (str): dmr file.
        result (str, optional): Filename to save result. If this is 
            not provided, the input file is overwritten. Defaults to None.
        subject (str or list, optional): subject or list of subjects 
            to keep. Defaults to None.
        study (str or list, optional): subject or list of subjects 
            to keep. Defaults to None.
        parameter (str or list, optional): parameter or list of 
            parameters to keep. Defaults to None.
        kwargs (dict): select parameters based on attributes in the 
            data dictionary.
    Returns:
        str : the resulting file
    """
    data = pydmr.rw.read(file)
    data = pydmr.pydict.dict_keep(data, subject, study, parameter, **kwargs)
    if result is None:
        pydmr.rw.write(file, data)
        return file
    else:
        pydmr.rw.write(result, data)
        return result



def concat(
        files:list, 
        result:str,
        cleanup=False,
    ):
    """Concatenate a list of dmr files into a single dmr file

    Args:
        files (list): dmr files to concatenate
        result (str): file path to the resulting dmr file
        cleanup (bool, optional): If set to True, the original files 
          are deleted after concatenating.
    Raises:
        ValueError: if duplicate indices exist in the file set.
    Returns:
        str: The result file
    """

    # combine dmr files
    dmr = {'data': {}}

    for i, file in enumerate(files):

        dmr_file = pydmr.rw.read(file)

        dmr['data'] = dmr['data'] | dmr_file['data']

        # Check dat all data dictionaries have the same columns
        if 'columns' in dmr_file:
            if i==0:
                dmr['columns'] = dmr_file['columns']
            elif 'columns' not in dmr:
                raise ValueError(
                    'Cannot concatenate: all data.csv files must have '
                    'the same optional variables (columns).'
                )
            elif dmr['columns'] != dmr_file['columns']:
                raise ValueError(
                    'Cannot concatenate: all data.csv files must have '
                    'the same optional variables (columns).'
                )

        for var in ['rois', 'pars', 'sdev']:
            if var in dmr_file:
                if var not in dmr:
                    dmr[var] = dmr_file[var]
                elif set(dmr_file[var].keys()).isdisjoint(set(dmr[var].keys())):
                    dmr[var] = dmr[var] | dmr_file[var]
                else:
                    raise ValueError(
                        f"Cannot concatenate: duplicate indices "
                        f"in {var}.csv of {dmr_file}."
                    )
                    

    pydmr.rw.write(result, dmr)

    if cleanup:
        for file in files:
            if file[-4:]=='.dmr':
                os.remove(file + '.zip')
            elif file[-8:] =='.dmr.zip':
                os.remove(file)
            else:
                os.remove(file + '.dmr.zip')

    return result


def append(
        file:str, 
        dmr:dict,
        format = 'flat',
    ):
    """Concatenate a list of dmr files into a single dmr file

    Args:
        file (list): dmr file to append to
        dmr (str): data to append to file
        format (str, optional): format of the data.
    Returns:
        str: The appended file
    """

    # Read flat dmr data
    dmr_orig = pydmr.rw.read(file)

    # Convert new data to flat
    dmr = pydmr.pydict.dict_to_flat(dmr, format)

    # Check dat all data dictionaries have the same columns
    data_error = False
    if 'columns' in dmr:
        if 'columns' not in dmr_orig:
            data_error = True
        elif dmr_orig['columns'] != dmr['columns']:
            data_error = True
    else:
        if 'columns' in dmr_orig:
            data_error = True
    if data_error:
        raise ValueError(
            'Cannot append: all data.csv files must have '
            'the same optional variables (columns).'
        )        

    dmr_orig['data'] = dmr_orig['data'] | dmr['data']

    for var in set(dmr.keys()) - {'data'}:
        if var in dmr_orig:
            if set(dmr[var].keys()).isdisjoint(set(dmr_orig[var].keys())):
                dmr_orig[var] = dmr_orig[var] | dmr[var]
            else:
                raise ValueError(
                    f"Cannot append: duplicate indices "
                    f"in {var}.csv of {dmr}."
                )
        else:
            dmr_orig[var] = dmr[var]

    pydmr.rw.write(file, dmr_orig)

    return file