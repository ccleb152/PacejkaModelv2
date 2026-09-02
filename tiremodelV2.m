%% Tire Model V2 %%
% Last updated: 3/20/2025

% To run the tire model, you must have access to each referenced function
% as well as Crimson Racing's Extracted Tire Data

clear
clc
close all

%% User Inputs

Tire = 'Radial_S6B';
Tire_title = 'Radial S6B';
Tire_compound = 'Radial';
Round = 4;
Run = 33;
Fz_nom = [50];
%% Loading TTC Data %%

[file, path] = uigetfile('.mat', 'Select TTC .mat Files', ...
    'C:\OneDrive - The University of Alabama\CrimsonStorage\Engineering\Full Car Simulation Codes\Non-Lapsim Codes\Tire Data\MatLab Codes', ...
    'MultiSelect', 'on');

% Check if files were selected
if isequal(file, 0)
    disp('No files selected');
    return;
end

if ~iscell(file)
    file = {file};
end

% Force patterns to search for in filenames (exact matches)

force_patterns = strcat('(?<!\d)', string(Fz_nom), 'FZ(?!\d)'); % Regex for exact matches
alpha_data = {};
Fy_data = {};
gamma_data = {};
Fx_data = {};

% Initialize results struct (optional but cleaner)
results = struct();

% Iterate over each selected file
for f = 1:numel(file) % Number of selected files
    % Full filepath for the current file
    fullfilepath = fullfile(path, file{f});
    data = load(fullfilepath);
    disp(['Loaded file: ', fullfilepath]);
    
    % Identify the correct force level using precise regex matching
    matched_force = '';
    for level = force_patterns
        if ~isempty(regexp(file{f}, level, 'once')) % Exact match
            matched_force = char(level); % Convert to string
            matched_force = regexprep(matched_force, '[^0-9]', ''); % Extract just the force value
            break;
        end
    end
    
    if isempty(matched_force)
        disp(['No matching force level found in file: ', file{f}]);
        continue; % Skip this file if no match
    end
    
    % Variable assignment logic
    required_patterns = {'^FY_.*', '^SA_.*', '^FZ_.*', '^FX_.*', '^SL_.*', 'MZ_.*'};
    base_variable_names = {'TTC_fy', 'TTC_sa', 'TTC_fz', 'TTC_fx', 'TTC_sl', 'TTC_mz'};
    
    for k = 1:numel(required_patterns)
        pattern = required_patterns{k};
        variablenames = fieldnames(data);
        matches = regexp(variablenames, pattern, 'match');
        
        matchedvariable = '';
        for i = 1:numel(matches)
            if ~isempty(matches{i})
                matchedvariable = variablenames{i};
                break;
            end
        end
        
        if ~isempty(matchedvariable)
            % Assign variable with force level appended (e.g., TTC_fy_150FZ)
            assigned_variable = sprintf('%s_%sFZ', base_variable_names{k}, matched_force);
            
            % Store in struct or assign in base workspace
            results.(assigned_variable) = data.(matchedvariable);
            assignin('base', assigned_variable, data.(matchedvariable)); % Optional if struct is used
            
            disp(['Matched variable: ', matchedvariable, ' -> ', assigned_variable]);
        else
            disp(['No matching variable found for pattern: ', pattern, ' in file: ', file{f}]);
        end
    end

    if min(eval(strcat('TTC_sa_', matched_force, 'FZ')))>-1 && max(eval(strcat('TTC_sa_', matched_force, 'FZ')))<1
        Type = 'FX';
    else
        Type = 'FY';
    end
end
%now we have TTC raw data saved in lbf and degrees
% need to call FY Parameters function and close figure, then plot fitted data against raw data

%% FY or FX data
if Type == 'FY'

    FYlegendEntries = {}; % initializing legend entries array
    FYplotHandles =[]; % initializing plot handles array
    colors = hsv(length(Fz_nom));
    FYrawDataPlotted = false;
%% FY approximations
    for level = 1:length(Fz_nom)
        
        cd 'C:\OneDrive - The University of Alabama\CrimsonStorage\Engineering\Vehicle Simulation Codes\Non-Lapsim Codes\Tire Data\MatLab Codes';

        [FY_ParameterList, yfit, Alpha] = Pacejka_Term_Finder_FY_V3(Round, Run, Tire, Fz_nom(level));
    
        Alpha_deg = Alpha.*(180/pi);
        ydata_lbf = yfit.Base/4.44822;
    
        fieldNameAlpha = sprintf('Alpha_deg_%dFZ', Fz_nom(level));
        fieldNameYdata = sprintf('ydata_lbf_%dFZ', Fz_nom(level));
        results.(fieldNameAlpha) = Alpha_deg;
        results.(fieldNameYdata) = ydata_lbf;
    
        close Figure 1
        FYfits = figure(2);
        FYfits.Name = 'Pacejka Fits';
        FYfits.NumberTitle = 'off';
        grid on
        color = colors(level, :);

        h1 = plot(Alpha_deg, ydata_lbf, 'LineWidth', 1.25, 'color', color);
        hold on
        FYplotHandles = [FYplotHandles, h1];
        FYlegendEntries{end+1} = sprintf('%d lbf', Fz_nom(level));
        
        %data tips maybe?
        [maxY, idxMax] = max(ydata_lbf);
        maxX = Alpha_deg(idxMax);
        [minY, idxMin] = min(ydata_lbf);
        minX = Alpha_deg(idxMin);

        dcm = datacursormode(FYfits);
        dcm.Enable = 'on';

        dTipMax = datatip(h1, maxX, maxY, 'FontSize',9);
        dTipMin = datatip(h1, minX, minY, 'FontSize',9);
 
        TTC_sa = sprintf('TTC_sa_%dFZ', Fz_nom(level));
        TTC_fy = sprintf('TTC_fy_%dFZ', Fz_nom(level));
    
        h2 = plot(eval(TTC_sa), eval(TTC_fy), 'Color','#616161', 'LineWidth',0.5);
        grid on

        if ~FYrawDataPlotted
            FYplotHandles = [FYplotHandles, h2];
            FYlegendEntries{end+1} = 'Raw Data';
            FYrawDataPlotted = true;
        end

        xlabel('Slip Angle (deg)')
        ylabel('Lateral Force (lbf)')
        title(strcat(Tire_title, ' Lateral Load vs Slip Angle'))
        hold on
                
    end

    %add legend outside loop
    legend(FYplotHandles, FYlegendEntries, 'Location', 'Best');
    
    FileName = strcat(Tire_title, ' Lateral vs Slip Angle Pacejka Fit');
    savefig(FYfits, strcat("CC's tire model folder\Fitted Parameters\",Tire_compound,'\', FileName, '.fig'))
    



%% MZ Curve fits
    mzLegendEntries = {};
    mzPlotHandles = [];
    mzRawDataPlotted = false;

    for level = 1:length(Fz_nom)

        [MZ_ParameterList, mzfit, Alpha] = Pacejka_Term_Finder_MZ_V1_redo(Round, Run, Tire, Fz_nom(level));

        Alpha_deg = Alpha.*(180/pi);
        mzdata_ftlb = mzfit.Base*3.281/4.44822;

        fieldNameAlpha = sprintf("Alpha_deg_%dFZ", Fz_nom(level));
        fieldNameMZdata = sprintf('mzdata_ftlb_%dFZ', Fz_nom(level));
        results.(fieldNameAlpha) = Alpha_deg;
        results.(fieldNameMZdata) = mzdata_ftlb;
        
        close Figure 1
        MZfits = figure(3);
        MZfits.Name = 'MZ Pacejka Fits';
        MZfits.NumberTitle = 'off';
        color = colors(level, :);
        grid on
        m1 = plot(Alpha_deg, mzdata_ftlb, 'LineWidth', 1.25, 'color', color);
        mzPlotHandles = [mzPlotHandles, m1];
        mzLegendEntries{end+1} = sprintf('%d lbf', Fz_nom(level));
        hold on

        TTC_sa = sprintf('TTC_sa_%dFZ', Fz_nom(level));
        TTC_mz = sprintf('TTC_mz_%dFZ', Fz_nom(level));

        m2 = plot(eval(TTC_sa), eval(TTC_mz), 'Color','#616161', 'LineWidth',0.5);
        grid on

        if ~mzRawDataPlotted
            mzPlotHandles = [mzPlotHandles, m2]; % Add raw data to legend once
            mzLegendEntries{end+1} = 'Raw Data';
            mzRawDataPlotted = true; % Prevent duplicate raw data legend entries
        end

        xlabel('Slip Angle (deg)')
        ylabel('Aligning Moment (ft-lb)')
        title(strcat(Tire_title, ' Aligning Moment vs Slip Angle'))
        hold on
        
    end

    legend(mzPlotHandles, mzLegendEntries, 'Location', 'Best');
    FileName = strcat(Tire_title, ' Aligning Moment vs Slip Angle Pacejka Fit');
    savefig(MZfits, strcat("CC's tire model folder\Fitted Parameters\",Tire_compound,'\', FileName, '.fig'))
    
%% FX
elseif Type == 'FX'

    for level = 1:length(Fz_nom)

        cd 'C:\OneDrive - The University of Alabama\CrimsonStorage\Engineering\Full Car Simulation Codes\Non-Lapsim Codes\Tire Data\MatLab Codes';

        [FX_ParameterList, yfit, kappa] = Pacejka_Term_Finder_FX_V4_Redo(Round, Run, Tire, Fz_nom);

        ydata_lbf = yfit.Combined.Base/4.44822;

        fieldNameKappa = sprintf('Kappa_%dFZ', Fz_nom(level));
        fieldNameYdata = sprintf('ydata_lbf_%dFZ', Fz_nom(level));
        results.(fieldNameKappa) = kappa;
        results.(fieldNameYdata) = ydata_lbf;
    
        close Figure 1
        FXfits = figure(4);
        FXfits.Name = 'FX Pacejka Fits';
        FXfits.NumberTitle = 'off';
        grid on
        plot(kappa, ydata_lbf, 'LineWidth', 1.25, 'color', 'r');
        hold on
    
        TTC_sl = sprintf('TTC_sl_%dFZ', Fz_nom(level));
        TTC_fx = sprintf('TTC_fx_%dFZ', Fz_nom(level));
    
        plot(eval(TTC_sl), eval(TTC_fx), 'b')
        grid on
        xlabel('Slip Ratio')
        ylabel('Longitudinal Force (lbf)')
        title(strcat(Tire_title, ' Longitudinal Force vs Slip Ratio'))
        hold on
    end

    FileName = strcat(Tire_title, ' Longitudinal vs Slip Ratio Pacejka Fit');
    savefig(FXfits, strcat("CC's tire model folder\Fitted Parameters\", FileName, '.fig'))

    % for level = 1:length(Fz_nom)
    % 
    %    [MX_ParameterList, mxfit, Alpha] = Pacejka_Term_Finder_MX_V1(Round, Run, Tire, Fz_nom(level)); 
    % 
    % end

end

%% potential interpolation happening... maybe

Fz_interp = [75 125 175 225];

interpolated_results = struct();

for fz = Fz_interp
    Alpha_combined = [];
    Fy_combined = [];

    for level = 1:length(Fz_nom)
        fieldNameAlpha = sprintf('Alpha_deg_%dFZ', Fz_nom(level));
        fieldNamYdata = sprintf('ydata_lbf_%dFZ', Fz_nom(level));

        if isfield(results, fieldNameAlpha) && isfield(results, fieldNameYdata)
            Alpha_combined = [Alpha_combined; results.(fieldNameAlpha)'];
            Fy_combined = [Fy_combined; results.(fieldNameYdata)'];
        end
    end

    [Alpha_unique, ia] = unique(Alpha_combined);
    Fy_interpolated = interp1(Fz_nom, Fy_combined(ia, :), fz, 'linear', 'extrap');

    interpolated_results.(sprintf('Alpha_deg_%dFZ', fz)) = Alpha_unique;
    interpolated_results.(sprintf('Fy_interp_%dFZ', fz)) = Fy_interpolated;

    figure(3)
    hold on
    plot(Alpha_unique, Fy_interpolated, 'LineWidth', 1.5, 'DisplayName', sprintf('%d lbf FZ (Interpolated)', fz));
end

% Overlay og data

for level = 1:length(Fz_nom)
    fieldNameAlpha = sprintf('Alpha_deg_%dFZ', Fz_nom(level));
    fieldNameYdata = sprintf('ydata_lbf_%dFZ', Fz_nom(level));

    if isfield(results, fieldNameAlpha) && isfield(results, fieldNameYdata)
        plot(results.(fieldNameAlpha), results.(fieldNameYdata), 'o', 'DisplayName', sprintf('%d lbf FZ (Raw)', Fz_nom(level)));
    end
end

% Finalize plot
grid on;
xlabel('Slip Angle (deg)');
ylabel('Lateral Force (lbf)');
titel(strcat(Tire_title, ' Interpolated Lateral Load vs Slip Angle'));
legend show;