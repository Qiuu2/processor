TAPS = 512; % No. of FIR taps
BIQUADS = 4; % No. of IIR biquad stages
N = 2*BIQUADS; %IIR filter order 
IIR_BANDS = 5; % No. of IIR bands per channel
WINDOW=256; % Block size
FS=48000; % Sample rate
FSH=FS/2; % Half of the sample rate
NCH=12; % No. of channels

%IIR bands 
b1fc = 250;
b2fc1 = 250; b2fc2 = 500;
b3fc1 = 500; b3fc2 = 2000;
b4fc1 = 2000; b4fc2 = 4000;
b5fc1 = 4000;

%Gains 
g11 = 1.0;
g22 = 0.8;
g33 = 0.6;
g44 = 0.4;
g55 = 0.2;

INPUT_LENGTH=TAPS+WINDOW-1;
ii=0:1:INPUT_LENGTH-1;

% Generate input signal with frequency components 100 Hz, 400 Hz, 1KHz, 3KHz, and 8KHz
x=sin(2*pi*ii*100/FS)+sin(2*pi*ii*400/FS)+sin(2*pi*ii*1000/FS)+sin(2*pi*ii*3000/FS)+sin(2*pi*ii*8000/FS); 

%All pass fir filter
b=zeros(1,TAPS);
b(1)=1;
a=1;

% filter input using FIR filter */ 
y1 = filter(b,a,x);

% Extract WINDOW input samples 
x2 = y1(TAPS:INPUT_LENGTH);

% IIR band 1 - low pass 250 Hz cutoff 
[b1 a1] = butter(N, b1fc/FSH, 'low');
[b2 a2] = butter(N/2, [b2fc1/FSH, b2fc2/FSH]);
[b3 a3] = butter(N/2, [b3fc1/FSH, b3fc2/FSH]);
[b4 a4] = butter(N/2, [b4fc1/FSH, b4fc2/FSH]);
[b5 a5] = butter(N, b5fc1/FSH, 'high');

% Derivce biquad coefficients
[sos1,g1]=tf2sos(b1,a1);
[sos2,g2]=tf2sos(b2,a2);
[sos3,g3]=tf2sos(b3,a3);
[sos4,g4]=tf2sos(b4,a4);
[sos5,g5]=tf2sos(b5,a5);

y21=x2; y22=x2; y23=x2; y24=x2; y25=x2;

% Filter using cascaded biquad
for i = 1:1:BIQUADS-1
    y21 = filter(sos1(i,1:3), sos1(i,4:6), y21);
    y22 = filter(sos2(i,1:3), sos2(i,4:6), y22);
    y23 = filter(sos3(i,1:3), sos3(i,4:6), y23);
    y24 = filter(sos4(i,1:3), sos4(i,4:6), y24);
    y25 = filter(sos5(i,1:3), sos5(i,4:6), y25);
end

figure; subplot(5,1,1); plot(y21);
subplot(5,1,2); plot(y22);
subplot(5,1,3); plot(y23);
subplot(5,1,4); plot(y24);
subplot(5,1,5); plot(y25);

% Apply gain to all IIR bands and add 
y21=y21*g1*g11; y22=y22*g2*g22; y23=y23*g3*g33; y24=y24*g4*g44; y25=y25*g5*g55;
y2 = y21 + y22 + y23 + y24 + y25;

%Plot the signals
signal_plot(x, WINDOW, FS, 'fir input' );
signal_plot(y1, WINDOW, FS, 'fir output' );
signal_plot(x2, WINDOW, FS, 'iir input' );
signal_plot(y2, WINDOW, FS, 'iir output' );

%Generate test data files 
cpf1 = sprintf('fir_coeffs.dat');
cpf2 = sprintf('iira_coeffs.dat');
cpf3 = sprintf('iirc_coeffs.dat');
gf   = sprintf('gains.dat');

fid = fopen(cpf1, 'w'); 
for i=1:1:NCH
    fprintf(fid,'%2.20e,\n',fliplr(b));
end
fclose(fid);

d=[0,0];

fid = fopen(cpf2, 'w'); 

for i=1:1:NCH
    for j = 1:1:BIQUADS
        %Multiply gain for the last stage
            fprintf(fid,'%2.20e,\n',sos1(j, 1));fprintf(fid,'%2.20e,\n',sos1(j, 2)); fprintf(fid,'%2.20e,\n',-sos1(j, 5));	fprintf(fid,'%2.20e,\n',sos1(j, 3));	fprintf(fid,'%2.20e,\n',-sos1(j, 6));	
            fprintf(fid,'%2.20e,\n',d(1)); fprintf(fid,'%2.20e,\n',d(2));	
    end    
    
    for j = 1:1:BIQUADS
             fprintf(fid,'%2.20e,\n',sos2(j, 1));fprintf(fid,'%2.20e,\n',sos2(j, 2)); fprintf(fid,'%2.20e,\n',-sos2(j, 5));	fprintf(fid,'%2.20e,\n',sos2(j, 3));	fprintf(fid,'%2.20e,\n',-sos2(j, 6));	
            fprintf(fid,'%2.20e,\n',d(1)); fprintf(fid,'%2.20e,\n',d(2));	
    end
  
   for j = 1:1:BIQUADS
            fprintf(fid,'%2.20e,\n',sos3(j, 1));fprintf(fid,'%2.20e,\n',sos3(j, 2)); fprintf(fid,'%2.20e,\n',-sos3(j, 5));	fprintf(fid,'%2.20e,\n',sos3(j, 3));	fprintf(fid,'%2.20e,\n',-sos3(j, 6));	
            fprintf(fid,'%2.20e,\n',d(1)); fprintf(fid,'%2.20e,\n',d(2));	
    end

    for j = 1:1:BIQUADS
            fprintf(fid,'%2.20e,\n',sos4(j, 1));fprintf(fid,'%2.20e,\n',sos4(j, 2)); fprintf(fid,'%2.20e,\n',-sos4(j, 5));	fprintf(fid,'%2.20e,\n',sos4(j, 3));	fprintf(fid,'%2.20e,\n',-sos4(j, 6));	
            fprintf(fid,'%2.20e,\n',d(1)); fprintf(fid,'%2.20e,\n',d(2));	
    end
    
    for j = 1:1:BIQUADS
             fprintf(fid,'%2.20e,\n',sos5(j, 1));fprintf(fid,'%2.20e,\n',sos5(j, 2)); fprintf(fid,'%2.20e,\n',-sos5(j, 5));	fprintf(fid,'%2.20e,\n',sos5(j, 3));	fprintf(fid,'%2.20e,\n',-sos5(j, 6));	
            fprintf(fid,'%2.20e,\n',d(1)); fprintf(fid,'%2.20e,\n',d(2));	
    end
end
fclose(fid);

fid = fopen(cpf3, 'w'); 

for i=1:1:NCH
    for j = 1:1:BIQUADS
            fprintf(fid,'%2.20e,\n',-sos1(j, 6)); fprintf(fid,'%2.20e,\n',-sos1(j, 5));	fprintf(fid,'%2.20e,\n',sos1(j, 3));	fprintf(fid,'%2.20e,\n',sos1(j, 2));fprintf(fid,'%2.20e,\n',sos1(j, 1)); 
    end    
    
    for j = 1:1:BIQUADS
             fprintf(fid,'%2.20e,\n',-sos2(j, 6)); fprintf(fid,'%2.20e,\n',-sos2(j, 5));	fprintf(fid,'%2.20e,\n',sos2(j, 3));	fprintf(fid,'%2.20e,\n',sos2(j, 2));fprintf(fid,'%2.20e,\n',sos2(j, 1)); 
    end    
     
    for j = 1:1:BIQUADS
            fprintf(fid,'%2.20e,\n',-sos3(j, 6)); fprintf(fid,'%2.20e,\n',-sos3(j, 5));	fprintf(fid,'%2.20e,\n',sos3(j, 3));	fprintf(fid,'%2.20e,\n',sos3(j, 2));fprintf(fid,'%2.20e,\n',sos3(j, 1)); 
     end    
      
    for j = 1:1:BIQUADS
            fprintf(fid,'%2.20e,\n',-sos4(j, 6)); fprintf(fid,'%2.20e,\n',-sos4(j, 5));	fprintf(fid,'%2.20e,\n',sos4(j, 3));	fprintf(fid,'%2.20e,\n',sos4(j, 2));fprintf(fid,'%2.20e,\n',sos4(j, 1)); 
    end    
    
    for j = 1:1:BIQUADS
            fprintf(fid,'%2.20e,\n',-sos5(j, 6)); fprintf(fid,'%2.20e,\n',-sos5(j, 5));	fprintf(fid,'%2.20e,\n',sos5(j, 3));	fprintf(fid,'%2.20e,\n',sos5(j, 2));fprintf(fid,'%2.20e,\n',sos5(j, 1)); 
     end    
end
fclose(fid);

fid = fopen(gf, 'w'); 
for i=1:1:NCH
    fprintf(fid,'%2.20e,\n',g1);
    fprintf(fid,'%2.20e,\n',g2);
    fprintf(fid,'%2.20e,\n',g3);
    fprintf(fid,'%2.20e,\n',g4);
    fprintf(fid,'%2.20e,\n',g5);
end
fclose(fid);

function signal_plot(x,size, sr, name)
% Plot in time domain
figure();subplot(2,1,1), plot(x);title(name);

%Plot in freqeuncy domain 
z = fft(x);f = 0:1:size/2-1;fs=f.*sr/size; subplot(2,1,2), plot(fs,abs(z(f+1:size/2)));xlabel('Frequency (Hz)');ylabel('Magnitude');
end