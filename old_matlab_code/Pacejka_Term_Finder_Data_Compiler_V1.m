 function [RawData] = Pacejka_Term_Finder_Data_Compiler_V1(Round, Run,Tire) 
Tire = replace(Tire,{' ';'-';'x'},{'_'});
SweepVars.Fz = string([50 100 150 200 250]');
SweepVars.IA = string([0  2]');
SweepVars.SA = string([0 3 6]');
SweepVars.P  = string([12]');
addpath(genpath('Data'))
RawDataVars = string(['FX';'FY';'SL']);

 
for n = 1:length(SweepVars.Fz)
        for j = 1:length(SweepVars.SA)
          for m = 1:length(SweepVars.IA)
            for k = 1:length(SweepVars.P)
                FileName = strcat('R',string(Round),'_Rn',string(Run),'_',Tire,'_', (SweepVars.P(k)),'psi_', (SweepVars.SA(j)),'SA_', (SweepVars.Fz(n)),'FZ_', (SweepVars.IA(m)),'IA_25.mat');
                for b = 1:length(RawDataVars)
                
                    DesiredVars = char(strcat(RawDataVars{b,1},'_R',string(Round),'_Rn',string(Run),'_',(SweepVars.Fz(n)),'FZ_',(SweepVars.P(k)),'P_',(SweepVars.IA(m)),'IA'));
                    if exist(FileName) ~= 0
                        Poland = load(FileName,string(DesiredVars));
                        DataVector = Poland.(DesiredVars)';
                        RawData.(strcat('P',SweepVars.P(k))).(strcat('SA',SweepVars.SA(j))).(strcat('IA',SweepVars.IA(m))).(DesiredVars) = DataVector;
                     
                    end
                end
            end
        end
    end
end
